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
from core.models.llm_bundle import LLMBundle
from api.deps import get_infra, get_retrieval, get_generation, get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Chat-specific thread pool for LLM streaming (separate from engine's retrieval pool)
_executor = ThreadPoolExecutor(max_workers=4)

_SENTINEL = "__STREAM_END__"


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
    model_id: Optional[int] = Field(None, description="指定模型 ID，留空使用默认模型")


# ---------------------------------------------------------------------------
# Chat endpoint (SSE streaming)
# ---------------------------------------------------------------------------

def _resolve_llm(body: ChatRequest, current_user: dict, infra: InfraBundle, db):
    """从数据库解析 LLM Bundle，优先使用 model_id 或默认模型，fallback 到 infra.llm_client"""
    if db is None:
        logger.info("数据库不可用，使用 .env 配置的 LLM")
        return infra.llm_client

    from core.models.tenant_llm_service import TenantLLMService
    service = TenantLLMService(db)
    tenant_id = current_user.get("username", "default")

    try:
        if body.model_id:
            # 指定了 model_id，直接查数据库
            model_config = service.get_model(tenant_id, body.model_id)
            if model_config:
                bundle = LLMBundle.from_config(
                    model_type=model_config["model_type"],
                    llm_factory=model_config["llm_factory"],
                    llm_name=model_config["llm_name"],
                    api_key=model_config["api_key"],
                    api_base=model_config.get("api_base", ""),
                )
                logger.info("使用指定模型 id=%s: %s/%s", body.model_id, model_config["llm_factory"], model_config["llm_name"])
                return bundle

        # 尝试获取默认 chat 模型
        model_config = service.get_default_model(tenant_id, "chat")
        if model_config:
            bundle = LLMBundle.from_config(
                model_type="chat",
                llm_factory=model_config["llm_factory"],
                llm_name=model_config["llm_name"],
                api_key=model_config["api_key"],
                api_base=model_config.get("api_base", ""),
            )
            logger.info("使用默认 chat 模型: %s/%s", model_config["llm_factory"], model_config["llm_name"])
            return bundle
    except Exception as e:
        logger.warning("从数据库获取模型失败，fallback 到 .env 配置: %s", e)

    # fallback 到 .env 配置
    logger.info("数据库无默认 chat 模型，使用 .env 配置的 LLM")
    return infra.llm_client


@router.post("/chat")
@limiter.limit(RATE_LIMIT_CHAT)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(get_infra),
    retrieval: RetrievalPipeline = Depends(get_retrieval),
    generation: GenerationService = Depends(get_generation),
    db = Depends(get_db),
):
    """流式对话接口"""
    # 从数据库解析 LLM（优先默认模型，fallback 到 .env）
    llm = _resolve_llm(body, current_user, infra, db)

    # 将前端传来的 history 转为 build_prompt 需要的格式
    history_dicts = [{"role": m.role, "content": m.content} for m in body.history]

    # 使用队列在线程和异步之间传递数据
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def generate_in_thread(prompt):
        """在线程池中运行的同步生成器，将结果放入队列"""
        try:
            for chunk in llm.stream_generate(prompt):
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
                    seen_sources = set()
                    for meta in contexts_data["metadatas"]:
                        src = meta["source"]
                        if src not in seen_sources:
                            seen_sources.add(src)
                            sources.append({
                                "source": src,
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

            # 持久化对话（verification 暂为 None，后续异步补充）
            conv_id = body.conversation_id or str(uuid.uuid4())[:8]
            title = body.history[0].content[:30] if body.history else body.message[:30]
            if len(title) > 30:
                title = title[:30] + "..."
            username = current_user["username"]

            all_messages = [
                {"role": m.role, "content": m.content} for m in body.history
            ]
            all_messages.append({"role": "user", "content": body.message})
            all_messages.append({"role": "assistant", "content": full_answer, "sources": sources, "verification": None})

            from api.conversations import save_conversation as _save
            await asyncio.to_thread(
                _save, conv_id, username, title, all_messages, body.mode
            )

            # 发送完成标记（verification 后续异步补充，不阻塞响应）
            done_data = json.dumps({
                "done": True,
                "full_answer": full_answer,
                "sources": sources,
                "verification": None,
                "conversation_id": conv_id,
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"

            # 引用核查（仅 RAG 模式且有上下文）—— 异步执行，不阻塞响应
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
                    # verification 完成后更新对话文件
                    all_messages[-1]["verification"] = verification
                    await asyncio.to_thread(
                        _save, conv_id, username, title, all_messages, body.mode
                    )
                    # 通过独立 SSE 事件推送 verification 结果到前端
                    verify_data = json.dumps({
                        "verification": verification,
                        "conversation_id": conv_id,
                    }, ensure_ascii=False)
                    yield f"event: verification\ndata: {verify_data}\n\n"
                except Exception as e:
                    logger.warning("Citation verification failed: %s", e)

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
