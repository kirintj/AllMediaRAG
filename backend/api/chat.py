import json
import asyncio
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.rate_limit import limiter, RATE_LIMIT_CHAT
from core.auth import get_current_user
from core.services import InfraBundle
from core.services.retrieval_pipeline import RetrievalPipeline
from core.services.generation_service import GenerationService

logger = logging.getLogger(__name__)

router = APIRouter()

# Chat-specific thread pool for LLM streaming (separate from engine's retrieval pool)
_executor = ThreadPoolExecutor(max_workers=4)

_SENTINEL = "__STREAM_END__"


# ---------------------------------------------------------------------------
# Dependency providers (read from app.state, no circular import)
# ---------------------------------------------------------------------------

def _get_infra(request: Request) -> InfraBundle:
    return request.app.state.infra


def _get_retrieval(request: Request) -> RetrievalPipeline:
    return request.app.state.retrieval


def _get_generation(request: Request) -> GenerationService:
    return request.app.state.generation


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=10000)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    mode: Literal["rag", "direct"] = Field("rag", description="对话模式")
    conversation_id: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")
    history: list[ChatMessage] = Field(default_factory=list, max_length=20, description="最近对话上下文")


# ---------------------------------------------------------------------------
# Chat endpoint (SSE streaming)
# ---------------------------------------------------------------------------

@router.post("/chat")
@limiter.limit(RATE_LIMIT_CHAT)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(_get_infra),
    retrieval: RetrievalPipeline = Depends(_get_retrieval),
    generation: GenerationService = Depends(_get_generation),
):
    """流式对话接口"""
    # 将前端传来的 history 转为 build_prompt 需要的格式
    history_dicts = [{"role": m.role, "content": m.content} for m in body.history]

    # 使用队列在线程和异步之间传递数据
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def generate_in_thread(prompt):
        """在线程池中运行的同步生成器，将结果放入队列"""
        try:
            for chunk in infra.llm_client.stream_generate(prompt):
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
        contexts = []
        verification = None
        try:
            if body.mode == "rag":
                # 使用完整检索管线（异步版本，查询理解并行化）
                contexts_data = await retrieval.full_retrieve_async(body.message)
                if contexts_data["documents"]:
                    for meta in contexts_data["metadatas"]:
                        sources.append({
                            "source": meta["source"],
                            "section": meta["section"]
                        })
                    context_list = []
                    for doc, meta in zip(contexts_data["documents"], contexts_data["metadatas"]):
                        context_list.append({"text": doc, "metadata": meta})
                    contexts = context_list
                    prompt = generation.build_prompt(body.message, context_list, history=history_dicts)
                else:
                    prompt = f"你是一个知识库问答助手。请简洁明了地回答以下问题：\n\n{body.message}"
            else:
                prompt = f"你是一个知识库问答助手。请简洁明了地回答以下问题：\n\n{body.message}"

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

            # 引用核查（仅 RAG 模式且有上下文）
            citation_verify_enabled = infra.settings.CITATION_VERIFY_ENABLED
            logger.info("Citation verify check: mode=%s, enabled=%s, contexts=%d, answer=%s",
                       body.mode, citation_verify_enabled, len(contexts), bool(full_answer.strip()))
            if body.mode == "rag" and citation_verify_enabled and contexts and full_answer.strip():
                try:
                    verification = infra.citation_verifier.verify(
                        body.message, full_answer, contexts,
                        retrieval_results=contexts_data
                    )
                    logger.info("Citation verification: confidence=%.2f, risk=%s",
                               verification["confidence"], verification["hallucination_risk"])
                except Exception as e:
                    logger.warning("Citation verification failed: %s", e)

            # 持久化对话（合并历史 + 本轮消息）
            conv_id = body.conversation_id or str(uuid.uuid4())[:8]
            title = body.history[0].content[:30] if body.history else body.message[:30]
            if len(title) > 30:
                title = title[:30] + "..."
            username = current_user["username"]

            # 合并前端传来的历史 + 本轮新消息
            all_messages = [
                {"role": m.role, "content": m.content} for m in body.history
            ]
            all_messages.append({"role": "user", "content": body.message})
            all_messages.append({"role": "assistant", "content": full_answer, "sources": sources})

            from api.conversations import save_conversation as _save
            await asyncio.to_thread(
                _save, conv_id, username, title, all_messages, body.mode
            )

            # 发送完成标记（包含 verification）
            done_data = json.dumps({
                "done": True,
                "full_answer": full_answer,
                "sources": sources,
                "verification": verification,
                "conversation_id": conv_id,
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"

        except Exception as e:
            logger.exception("SSE流式生成失败")
            yield f"event: error\ndata: {json.dumps({'error': str(e), 'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
