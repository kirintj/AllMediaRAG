import os
from typing import Generator

from embedding_service import EmbeddingService
from vector_store import VectorStore
from llm_client import LLMClient
from document_processor import DocumentProcessor


class RAGEngine:
    """RAG 引擎：组合各模块，提供完整的 RAG 查询接口"""

    def __init__(self, config):
        """初始化 RAG 引擎

        Args:
            config: 配置对象
        """
        self.embedding_service = EmbeddingService(config.EMBEDDING_MODEL_PATH)
        self.vector_store = VectorStore(config.CHROMA_PERSIST_DIR)
        self.llm_client = LLMClient(
            config.MIMO_API_KEY,
            config.MIMO_API_BASE,
            config.MIMO_MODEL
        )
        self.document_processor = DocumentProcessor(
            config.CHUNK_SIZE,
            config.CHUNK_OVERLAP
        )

        self.top_k = config.TOP_K
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
        self.max_history_turns = config.MAX_HISTORY_TURNS
        self.conversation_history: list[dict] = []

    def ingest_document(self, file_path: str) -> int:
        """导入文档，返回 chunk 数量

        Args:
            file_path: 文档文件路径

        Returns:
            处理的 chunk 数量
        """
        source = os.path.basename(file_path)
        chunks = self.document_processor.process_file(file_path)

        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = self.embedding_service.encode(texts)

        self.vector_store.add_documents(texts, embeddings, metadatas)

        return len(chunks)

    def retrieve(self, query: str, top_k: int = None) -> dict:
        """检索相关文档

        Args:
            query: 用户查询
            top_k: 返回数量，默认使用配置值

        Returns:
            检索结果
        """
        if top_k is None:
            top_k = self.top_k

        query_embedding = self.embedding_service.encode_single(query)
        results = self.vector_store.query(query_embedding, top_k)

        filtered = self.filter_by_similarity(results, self.similarity_threshold)

        return filtered

    def filter_by_similarity(self, results: dict, threshold: float) -> dict:
        """按相似度过滤结果

        Args:
            results: 原始检索结果
            threshold: 相似度阈值

        Returns:
            过滤后的结果
        """
        if not results["distances"]:
            return results

        filtered_docs = []
        filtered_metas = []
        filtered_dists = []

        for doc, meta, dist in zip(
            results["documents"],
            results["metadatas"],
            results["distances"]
        ):
            similarity = 1 - dist
            if similarity >= threshold:
                filtered_docs.append(doc)
                filtered_metas.append(meta)
                filtered_dists.append(dist)

        return {
            "documents": filtered_docs,
            "metadatas": filtered_metas,
            "distances": filtered_dists
        }

    def build_prompt(self, query: str, contexts: list[dict]) -> str:
        """构建 Prompt

        Args:
            query: 用户问题
            contexts: 检索到的上下文

        Returns:
            完整的 Prompt
        """
        context_parts = []
        for i, ctx in enumerate(contexts, 1):
            source = ctx["metadata"]["source"]
            section = ctx["metadata"]["section"]
            context_parts.append(f"[来源 {i}: {source} - {section}]\n{ctx['text']}")

        context_str = "\n\n".join(context_parts)

        history_str = ""
        if self.conversation_history:
            history_lines = []
            for msg in self.conversation_history[-self.max_history_turns * 2:]:
                role = "用户" if msg["role"] == "user" else "助手"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines)

        prompt = f"""你是一个 Python 技术文档问答助手。请基于以下参考文档内容回答用户问题。

要求：
1. 仅基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确说明"文档中未找到相关信息"
3. 回答要准确、简洁，必要时引用代码示例
4. 在回答末尾标注引用的文档来源
5. 结合对话历史理解上下文，避免重复已说明的内容

---参考文档---
{context_str}
"""

        if history_str:
            prompt += f"""
---对话历史---
{history_str}
"""

        prompt += f"""
---用户问题---
{query}"""

        return prompt

    def query_stream(self, question: str) -> Generator[dict, None, None]:
        """流式查询，返回 {answer_chunk, sources}

        Args:
            question: 用户问题

        Yields:
            包含 answer_chunk 和 sources 的字典
        """
        results = self.retrieve(question)

        # 将 results 转换为 contexts 格式
        contexts = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            contexts.append({
                "text": doc,
                "metadata": meta
            })

        prompt = self.build_prompt(question, contexts)

        sources = []
        for ctx in contexts:
            sources.append({
                "source": ctx["metadata"]["source"],
                "section": ctx["metadata"]["section"],
                "text": ctx["text"][:200] + "..." if len(ctx["text"]) > 200 else ctx["text"]
            })

        full_answer = ""
        for chunk in self.llm_client.stream_generate(prompt):
            full_answer += chunk
            yield {
                "answer_chunk": chunk,
                "full_answer": full_answer,
                "sources": sources
            }

        self.update_history(question, full_answer)

    def update_history(self, question: str, answer: str):
        """更新对话历史

        Args:
            question: 用户问题
            answer: 助手回答
        """
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": answer})

        max_messages = self.max_history_turns * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
