"""RegionChunker — 按区域类型进行类型感知的 Chunk。

接收 VLMExtractor 输出的 DocumentRegion 列表，根据区域类型
（text/table/figure/equation/header）采用不同的分块策略，
产出统一格式的 chunk 列表供 IngestionService 写入向量库。

设计决策：
- text 区域委托给注入的 ChunkingStrategy，因为文本切分有多种
  算法（语义、递归、固定大小），RegionChunker 不应绑定具体策略；
- table/equation 不切分，因为它们是完整语义单元，拆分会破坏结构；
- figure 单独处理图片存储，因为图片需要落盘到 ImageStore，
  这是多模态 RAG 区别于纯文本 RAG 的关键路径。
"""

from ..models.document_region import DocumentRegion


class RegionChunker:
    """按区域类型分块：text 委托策略，table/figure/equation 单 chunk。"""

    def __init__(self, text_chunking_strategy):
        """初始化 RegionChunker。

        Args:
            text_chunking_strategy: 实现 ChunkingStrategy 接口的切分策略，
                text 类型的区域会委托给该策略的 split 方法。
        """
        # 为什么用下划线前缀的属性名：标识这是内部状态，
        # 外部不应直接替换，只通过构造函数注入。
        self._text_chunking_strategy = text_chunking_strategy

    def chunk(
        self,
        regions: list[DocumentRegion],
        source: str,
        image_store=None,
    ) -> list[dict]:
        """将 DocumentRegion 列表转为统一格式的 chunk 列表。

        Args:
            regions: VLMExtractor 提取的文档区域列表
            source: 来源文档标识（如文件名），写入每个 chunk 的文本前缀
            image_store: 可选的 ImageStore 实例，figure 区域会调用其 save

        Returns:
            chunk 列表，每个 chunk 包含 "text" 和 "metadata" 字段，
            末尾追加 chunk_index 用于标识顺序。
        """
        chunks = []
        # 为什么用局部变量跟踪 section 而非放在 region 上：
        # DocumentRegion 是上游产出的不可变 DTO，不应被 chunker 修改；
        # section 跟踪是 chunker 的职责，用局部变量隔离更清晰。
        current_section = ""

        for region in regions:
            # 为什么 header 类型不产出 chunk 本身：
            # header 的内容已经通过 current_section 传递给了后续 chunk，
            # 单独产出一个仅含标题的 chunk 会稀释检索结果的信息密度。
            if region.type == "header":
                current_section = region.content
                continue

            if region.type == "text":
                region_chunks = self._chunk_text(region, source, current_section)
            elif region.type == "figure":
                region_chunks = self._chunk_figure(
                    region, source, current_section, image_store
                )
            else:
                # table 和 equation 走统一的单 chunk 路径，
                # 因为它们都是不可拆分的语义单元。
                region_chunks = self._chunk_single(
                    region, source, current_section, region_type=region.type
                )

            chunks.extend(region_chunks)

        # 为什么在循环结束后统一添加 chunk_index 而非在每个 chunk 内部：
        # 统一编号可以避免多个区域类型的 chunk 产生重复或跳跃的索引，
        # 确保最终 chunk_index 是全局连续的。
        for i, chunk in enumerate(chunks):
            chunk["metadata"]["chunk_index"] = i

        return chunks

    def _chunk_text(
        self, region: DocumentRegion, source: str, section: str
    ) -> list[dict]:
        """将 text 区域委托给 text_chunking_strategy 进行切分。

        策略返回的 ChunkData 列表会被包装成统一的 chunk 格式，
        每个 chunk 前缀加上来源和章节信息，便于检索时定位上下文。
        """
        # 为什么先调用 split 再包装：保持策略的纯切分职责不变，
        # source/section 的组装由 RegionChunker 负责，
        # 这样策略可以独立于文档元数据被复用。
        sub_chunks = self._text_chunking_strategy.split(region.content)

        results = []
        for sub in sub_chunks:
            text = self._format_text(source, section, sub["content"])
            results.append({
                "text": text,
                "metadata": {
                    **sub.get("metadata", {}),
                    "source": source,
                    "section": section,
                    "region_type": "text",
                },
            })
        return results

    def _chunk_single(
        self,
        region: DocumentRegion,
        source: str,
        section: str,
        region_type: str,
    ) -> list[dict]:
        """为 table / equation 等不可拆分区域生成单个 chunk。

        为什么不切分：表格和公式是结构化语义单元，
        拆分后行列对应关系或公式完整性会被破坏。
        """
        text = self._format_text(source, section, region.content)
        return [{
            "text": text,
            "metadata": {
                "source": source,
                "section": section,
                "region_type": region_type,
            },
        }]

    def _chunk_figure(
        self,
        region: DocumentRegion,
        source: str,
        section: str,
        image_store,
    ) -> list[dict]:
        """处理 figure 区域：保存图片到 image_store，生成含图片元数据的 chunk。

        为什么 figure 需要特殊处理：figure 是多模态 RAG 的核心，
        除了文本描述外还需要存储图片路径，以便检索命中后展示原图。
        """
        metadata = {
            "source": source,
            "section": section,
            "region_type": "figure",
        }

        # 为什么检查 image_store 是否存在：允许在无图片存储的场景下
        # （如纯文本模式或单元测试）优雅降级，而非强制要求必须有 store。
        if image_store is not None and region.image_base64:
            # 为什么传 source 给 save：ImageStore 需要知道图片来源，
            # 以便在文档删除时按来源清理对应的图片文件。
            image_path = image_store.save(region.image_base64, source=source)
            metadata["has_image"] = True
            metadata["image_path"] = image_path

        text = self._format_text(source, section, region.content)
        return [{
            "text": text,
            "metadata": metadata,
        }]

    @staticmethod
    def _format_text(source: str, section: str, content: str) -> str:
        """将来源、章节、内容组装为统一的文本格式。

        为什么用 [{source} - {section}] 前缀：
        这个前缀会作为 embedding 的一部分被编码，
        让检索时 "哪个文档的哪个章节" 成为语义信号的一部分，
        提高跨文档检索时的定位精度。
        """
        # 为什么 section 为空时用空字符串而非 "未知章节"：
        # 避免 "未知章节" 成为无意义的噪声 token 参与 embedding，
        # 空字符串在文本中不会引入额外语义。
        prefix = f"[{source} - {section}]" if section else f"[{source}]"
        return f"{prefix}\n{content}"
