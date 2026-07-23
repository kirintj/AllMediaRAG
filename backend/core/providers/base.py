"""Provider 抽象接口与查询表达式类。

表达式体系与 RAGFlow 对齐，用于向量存储层的统一查询。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generator


# ---------------------------------------------------------------------------
# 查询表达式
# ---------------------------------------------------------------------------

@dataclass
class MatchTextExpr:
    """全文检索表达式"""
    fields: list[str]              # 检索字段 ["text"]
    matching_text: str             # 查询文本
    topn: int = 10                 # 返回数量
    extra_options: dict | None = None  # {"minimum_should_match": "70%"}


@dataclass
class MatchDenseExpr:
    """向量检索表达式"""
    embedding_data: list[float]    # 查询向量
    topn: int = 10                 # 返回数量
    distance_type: str = "cosine"
    extra_options: dict | None = None  # {"similarity": 0.1} 阈值


@dataclass
class FusionExpr:
    """多信号融合表达式"""
    method: str                    # "weighted_sum" / "rrf"
    topn: int = 10                 # 融合后返回数量
    fusion_params: dict | None = None  # {"weights": "0.7,0.3"}


class OrderByExpr:
    """排序表达式，支持链式调用"""

    def __init__(self):
        self._clauses: list[tuple[str, str]] = []  # [(field, "asc"|"desc"), ...]

    def asc(self, field: str) -> "OrderByExpr":
        self._clauses.append((field, "asc"))
        return self

    def desc(self, field: str) -> "OrderByExpr":
        self._clauses.append((field, "desc"))
        return self

    @property
    def clauses(self) -> list[tuple[str, str]]:
        return list(self._clauses)


# 通用 MatchExpr 联合类型
MatchExpr = MatchTextExpr | MatchDenseExpr | FusionExpr


# ---------------------------------------------------------------------------
# 文件读取器
# ---------------------------------------------------------------------------

class FileReader(ABC):
    """文档读取器抽象接口
    所有文件读取器必须实现此接口。
    """

    @abstractmethod
    def read(self, file_path: str) -> str:
        """读取文件内容，返回纯文本"""
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        pass

    def can_handle(self, file_path: str) -> bool:
        """判断是否能处理该文件"""
        import os
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions()


# ---------------------------------------------------------------------------
# 向量存储（与 RAGFlow DocStoreConnection 对齐）
# ---------------------------------------------------------------------------

class VectorStoreProvider(ABC):
    """向量存储抽象接口。

    所有向量存储实现必须实现此接口。
    表达式驱动的统一查询，将混合检索下沉到存储层。
    """

    # ── 连接信息 ──

    @abstractmethod
    def db_type(self) -> str:
        """返回数据库类型标识，如 'elasticsearch'"""
        pass

    @abstractmethod
    def health(self) -> dict:
        """返回存储健康状态"""
        pass

    # ── 索引管理 ──

    @abstractmethod
    def create_idx(self, index_name: str, vector_size: int):
        """创建索引"""
        pass

    @abstractmethod
    def delete_idx(self, index_name: str = ""):
        """删除索引（空字符串表示当前索引）"""
        pass

    @abstractmethod
    def index_exist(self, index_name: str) -> bool:
        """检查索引是否存在"""
        pass

    # ── 统一查询（核心方法）──

    @abstractmethod
    def search(
        self,
        select_fields: list[str],
        condition: dict | None,
        match_expressions: list,
        order_by: Any | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> dict:
        """统一检索。

        Returns:
            {"documents": [...], "metadatas": [...], "distances": [...], "total": int}
        """
        pass

    # ── CRUD ──

    @abstractmethod
    def insert(self, rows: list[dict]) -> list[str]:
        """批量插入。返回错误列表（空 = 全部成功）。

        rows 每项: {"id", "text", "text_raw", "embedding", "source", "metadata", ...}
        """
        pass

    @abstractmethod
    def get(self, doc_id: str) -> dict | None:
        """按 ID 获取单个文档"""
        pass

    @abstractmethod
    def delete(self, condition: dict) -> int:
        """条件删除，返回删除数量"""
        pass

    @abstractmethod
    def update(self, condition: dict, new_value: dict) -> bool:
        """条件更新"""
        pass

    # ── 结果解析（便捷方法）──

    def get_total(self, res: dict) -> int:
        """获取结果总数"""
        return res.get("total", 0)

    def get_doc_ids(self, res: dict) -> list[str]:
        """获取结果中的文档 ID 列表"""
        return [m.get("id", "") for m in res.get("metadatas", []) if m.get("id")]

    def get_fields(self, res: dict, fields: list[str]) -> dict[str, dict]:
        """从结果中提取指定字段，返回 {doc_id: {field: value}}"""
        result = {}
        for meta in res.get("metadatas", []):
            doc_id = meta.get("id", "")
            if doc_id:
                result[doc_id] = {f: meta.get(f) for f in fields}
        return result

    # ── 兼容旧接口（供尚未迁移的调用方使用）──

    def get_all_sources(self) -> list[str]:
        """获取所有来源（兼容旧接口）"""
        res = self.search(["source"], None, [], limit=99999)
        seen: set[str] = set()
        sources: list[str] = []
        for m in res.get("metadatas", []):
            src = m.get("source", "")
            if src and src not in seen:
                seen.add(src)
                sources.append(src)
        return sources

    def get_document_count(self) -> int:
        """获取文档总数（兼容旧接口）"""
        res = self.search(["id"], None, [], limit=0)
        return res.get("total", 0)

    def get_source_details(self) -> list[dict]:
        """获取每个来源的详情（兼容旧接口）"""
        res = self.search(["source"], None, [], limit=99999)
        counts: dict[str, int] = {}
        for m in res.get("metadatas", []):
            src = m.get("source", "")
            if src:
                counts[src] = counts.get(src, 0) + 1
        return [{"source": s, "chunks": c} for s, c in counts.items()]

    def get_overview(self) -> dict:
        """获取概览（兼容旧接口）"""
        source_details = self.get_source_details()
        sources = [d["source"] for d in source_details]
        return {
            "sources": sources,
            "source_details": source_details,
            "document_count": self.get_document_count(),
        }

    def get_all_documents(self) -> list[dict]:
        """获取所有文档（兼容旧接口）"""
        res = self.search(["id", "text", "metadata"], None, [], limit=99999)
        docs = []
        for meta in res.get("metadatas", []):
            docs.append({
                "id": meta.get("id", ""),
                "text": meta.get("text", ""),
                "metadata": meta.get("metadata", {}),
            })
        return docs

    def close(self):
        """释放资源"""
        pass


# ---------------------------------------------------------------------------
# Embedding / LLM
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Embedding 模型抽象接口"""

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def encode_single(self, text: str) -> list[float]:
        pass


class LLMProvider(ABC):
    """LLM 抽象接口"""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        pass
