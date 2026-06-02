import json
import asyncio
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# 延迟导入 RAG 引擎
engine = None
_executor = ThreadPoolExecutor(max_workers=4)

_SENTINEL = "__STREAM_END__"

def get_engine():
    global engine
    if engine is None:
        from config import config
        from rag_engine import RAGEngine
        engine = RAGEngine(config)
    return engine

class ChatRequest(BaseModel):
    message: str
    mode: str = "rag"  # "rag" or "direct"
    conversation_id: Optional[str] = None

@router.post("/chat")
async def chat(request: ChatRequest):
    """流式对话接口"""
    engine = get_engine()

    # 使用队列在线程和异步之间传递数据
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def generate_in_thread(prompt):
        """在线程池中运行的同步生成器，将结果放入队列"""
        try:
            for chunk in engine.llm_client.stream_generate(prompt):
                asyncio.run_coroutine_threadsafe(
                    queue.put(chunk), loop
                )
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                queue.put(f"__ERROR__:{e}"), loop
            )
        finally:
            asyncio.run_coroutine_threadsafe(
                queue.put(_SENTINEL), loop
            )

    async def generate():
        sources = []
        try:
            if request.mode == "rag":
                contexts = engine.retrieve(request.message)
                if contexts["documents"]:
                    for meta in contexts["metadatas"]:
                        sources.append({
                            "source": meta["source"],
                            "section": meta["section"]
                        })
                    context_list = []
                    for doc, meta in zip(contexts["documents"], contexts["metadatas"]):
                        context_list.append({"text": doc, "metadata": meta})
                    prompt = engine.build_prompt(request.message, context_list)
                else:
                    prompt = f"你是一个 Python 技术专家。请简洁明了地回答以下问题：\n\n{request.message}"
            else:
                prompt = f"你是一个 Python 技术专家。请简洁明了地回答以下问题：\n\n{request.message}"

            # 在线程池中启动流式生成
            loop.run_in_executor(_executor, generate_in_thread, prompt)

            # 从队列读取结果并 yield
            full_answer = ""
            while True:
                chunk = await queue.get()
                if chunk == _SENTINEL:
                    break
                if isinstance(chunk, str) and chunk.startswith("__ERROR__:"):
                    error_msg = chunk[len("__ERROR__:"):]
                    yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
                    return
                full_answer += chunk
                data = json.dumps({
                    "chunk": chunk,
                    "full_answer": full_answer,
                    "sources": sources
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"

            # 更新引擎历史
            engine.update_history(request.message, full_answer)

            # 持久化对话
            conv_id = request.conversation_id or str(uuid.uuid4())[:8]
            title = request.message[:30] + ("..." if len(request.message) > 30 else "")
            from api.conversations import save_conversation as _save
            _save(conv_id, title, [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": full_answer, "sources": sources},
            ], request.mode)

            # 发送完成标记
            done_data = json.dumps({
                "done": True,
                "full_answer": full_answer,
                "sources": sources,
                "conversation_id": conv_id,
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.delete("/history")
async def clear_history():
    """清空对话历史"""
    engine = get_engine()
    engine.clear_history()
    return {"message": "对话历史已清空"}
