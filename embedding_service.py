from sentence_transformers import SentenceTransformer

class EmbeddingService:
    """Embedding 服务：加载 bge 模型，提供向量编码接口"""

    def __init__(self, model_path: str):
        """初始化 Embedding 服务

        Args:
            model_path: 模型路径或 HuggingFace 模型 ID
        """
        self.model = SentenceTransformer(model_path)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """批量编码文本为向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def encode_single(self, text: str) -> list[float]:
        """编码单条文本

        Args:
            text: 单条文本

        Returns:
            向量
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
