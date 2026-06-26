"""Generation Service - prompt building and streaming generation."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Generator

logger = logging.getLogger(__name__)

# Shared thread pool for post-generation parallel tasks
_post_gen_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="post-gen")


class GenerationService:
    """Handles prompt construction and LLM streaming generation.

    Extracted from RAGEngine as part of the service layer reorganization.
    Delegates retrieval to a RetrievalPipeline injected at construction time.
    """

    def __init__(self, infra, retrieval_pipeline):
        self._llm_client = infra.llm_client
        self._classifier = infra.classifier
        self._citation_verifier = infra.citation_verifier
        self._citation_verify_enabled = infra.settings.CITATION_VERIFY_ENABLED
        self._self_rag_reflector = infra.self_rag_reflector
        self._self_rag_enabled = infra.settings.SELF_RAG_ENABLED
        self._retrieval = retrieval_pipeline  # cross-service dependency
        # 为什么在 init 而非运行时获取：image_store 和多模态配置在服务生命周期内不变，
        # 提前注入避免每次查询时重复访问 infra，同时便于单元测试 mock。
        self._image_store = getattr(infra, "image_store", None)
        self._multimodal_enabled = getattr(infra.settings, "MULTIMODAL_GENERATION", False)
        self._max_images = getattr(infra.settings, "MULTIMODAL_MAX_IMAGES", 3)

    # ------------------------------------------------------------------
    # Prompt building (pure function, no external state)
    # ------------------------------------------------------------------

    def build_prompt(self, query: str, contexts: list[dict], history: list[dict] = None) -> str:
        """构建结构化 Prompt

        改进点：
        - 按来源去重并标注可靠性（high/medium/low）
        - 明确引用格式指令
        - 区分"文档支持的回答"和"推测"

        Args:
            query: 用户问题
            contexts: 检索到的上下文 [{"text": str, "metadata": dict}, ...]
            history: 对话历史 [{role, content}, ...]，由调用方传入

        Returns:
            完整的 Prompt
        """
        # 按来源去重，保留每个来源中最相关的 chunk
        seen_sources = {}
        for ctx in contexts:
            source = ctx["metadata"].get("source", "未知")
            if source not in seen_sources:
                seen_sources[source] = []
            seen_sources[source].append(ctx)

        # 构建结构化上下文（Parent-Child 策略自动使用 parent 文本）
        context_parts = []
        for i, (source, chunks) in enumerate(seen_sources.items(), 1):
            texts = [c["metadata"].get("parent_text", c["text"]) for c in chunks[:2]]
            combined_text = "\n...\n".join(texts)
            section = chunks[0]["metadata"].get("section", "")
            label = f"{source} - {section}" if section else source
            context_parts.append(f"[来源 {i}] {label}\n{combined_text}")

        context_str = "\n\n".join(context_parts)

        # 对话历史
        history_str = ""
        if history:
            history_lines = []
            for msg in history[-10:]:  # 最多保留最近 10 轮
                role = "用户" if msg["role"] == "user" else "助手"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines)

        prompt = f"""你是一个知识库文档问答助手。请基于以下参考文档回答用户问题。

## 参考文档

{context_str}

## 回答要求

1. **优先引用高相关度来源**，使用 [来源 N] 格式标注信息出处
2. **仅基于文档内容回答**，不要编造文档中不存在的信息
3. 如果参考文档不足以完整回答，明确说明哪些部分是基于文档、哪些是推测
4. 对于多部分问题，逐点结构化回答
5. 必要时引用代码示例，保持格式清晰
6. 结合对话历史理解上下文，避免重复已说明的内容
"""

        if history_str:
            prompt += f"""
## 对话历史

{history_str}
"""

        prompt += f"""
## 用户问题

{query}"""

        return prompt

    # ------------------------------------------------------------------
    # Multimodal image extraction
    # ------------------------------------------------------------------

    def _extract_images_from_contexts(self, contexts: list[dict]) -> list[str]:
        """从检索结果中取出 figure chunk 的原图 base64

        为什么在 GenerationService 而非 RetrievalPipeline 中做：
        检索阶段只关心文本匹配度，不应因为加载图片增加延迟；
        图片加载只在确定要生成回答时才需要。
        """
        if not self._multimodal_enabled or not self._image_store:
            return []

        images = []
        for ctx in contexts:
            meta = ctx.get("metadata", {})
            if meta.get("has_image") and meta.get("image_path"):
                img_b64 = self._image_store.load_base64(meta["image_path"])
                if img_b64:
                    images.append(img_b64)

        return images[:self._max_images]

    # ------------------------------------------------------------------
    # Streaming query (SSE generator)
    # ------------------------------------------------------------------

    def query_stream(self, question: str, history: list[dict] = None) -> Generator[dict, None, None]:
        """流式查询，返回 {answer_chunk, sources, verification}

        Args:
            question: 用户问题
            history: 对话历史 [{role, content}, ...]

        Yields:
            包含 answer_chunk、sources 和 verification 的字典
        """
        results = self._retrieval.full_retrieve(question)

        # 查询分类（用于决定是否启用 Self-RAG）
        try:
            intent = self._classifier.classify(question)
            intent_type = intent.get("intent_type", "factoid")
        except Exception:
            intent_type = "factoid"

        # 将 results 转换为 contexts 格式
        # Parent-Child 策略：如果 metadata 中有 parent_text，用 parent 替换 child
        contexts = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            text = meta.get("parent_text", doc)
            contexts.append({
                "text": text,
                "metadata": meta
            })

        prompt = self.build_prompt(question, contexts, history=history)

        sources = []
        seen_sources = set()
        for ctx in contexts:
            src = ctx["metadata"]["source"]
            if src not in seen_sources:
                seen_sources.add(src)
                sources.append({
                    "source": src,
                    "section": ctx["metadata"]["section"],
                    "text": ctx["text"][:200] + "..." if len(ctx["text"]) > 200 else ctx["text"]
                })

        full_answer = ""
        # 提取图片（仅在启用多模态时）
        images = self._extract_images_from_contexts(contexts)

        # 为什么传 images 参数：当 contexts 包含 figure chunk 时，
        # LLM 能同时看到图表描述和原图，生成更准确的回答。
        for chunk in self._llm_client.stream_generate(prompt, images=images):
            full_answer += chunk
            yield {
                "answer_chunk": chunk,
                "full_answer": full_answer,
                "sources": sources
            }

        # Self-RAG 反思 + 引用核查（并行执行）
        reflection = None
        verification = None

        run_self_rag = (self._self_rag_enabled
                        and self._self_rag_reflector.should_reflect(intent_type)
                        and contexts and full_answer.strip())
        run_citation = self._citation_verify_enabled and contexts and full_answer.strip()

        if run_self_rag and run_citation:
            # 并行：Self-RAG 和 Citation 同时执行
            future_rag = _post_gen_executor.submit(
                self._self_rag_reflector.reflect, question, full_answer, contexts)
            future_cite = _post_gen_executor.submit(
                self._citation_verifier.verify, question, full_answer, contexts)
            try:
                reflection = future_rag.result()
                if reflection and reflection.get("has_gaps") and reflection.get("supplement"):
                    supplement = reflection["supplement"]
                    full_answer += f"\n\n**补充说明：**\n{supplement}"
                    yield {
                        "answer_chunk": f"\n\n**补充说明：**\n{supplement}",
                        "full_answer": full_answer,
                        "sources": sources,
                    }
            except Exception as e:
                logger.warning("Self-RAG reflection failed: %s", e)
            try:
                verification = future_cite.result()
                logger.info("Citation verification: confidence=%.2f, risk=%s",
                            verification["confidence"], verification["hallucination_risk"])
            except Exception as e:
                logger.warning("Citation verification failed: %s", e)
        elif run_self_rag:
            try:
                reflection = self._self_rag_reflector.reflect(question, full_answer, contexts)
                if reflection and reflection.get("has_gaps") and reflection.get("supplement"):
                    supplement = reflection["supplement"]
                    full_answer += f"\n\n**补充说明：**\n{supplement}"
                    yield {
                        "answer_chunk": f"\n\n**补充说明：**\n{supplement}",
                        "full_answer": full_answer,
                        "sources": sources,
                    }
            except Exception as e:
                logger.warning("Self-RAG reflection failed: %s", e)
        elif run_citation:
            try:
                verification = self._citation_verifier.verify(question, full_answer, contexts)
                logger.info("Citation verification: confidence=%.2f, risk=%s",
                            verification["confidence"], verification["hallucination_risk"])
            except Exception as e:
                logger.warning("Citation verification failed: %s", e)

        # 最终结果包含 verification
        yield {
            "answer_chunk": "",
            "full_answer": full_answer,
            "sources": sources,
            "verification": verification,
            "done": True
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release resources (no-op for now)."""
        pass
