import os
import uuid
import logging
from datetime import datetime, timezone

from core.index_manager import IndexManager

logger = logging.getLogger(__name__)


class IngestionService:
    """文档摄入服务：负责文档的索引、删除与增量同步。"""

    def __init__(self, infra):
        self._infra = infra
        self._document_processor = infra.document_processor
        self._embedding_service = infra.embedding_service
        self._doc_store = infra.vector_store  # ElasticsearchStore
        self._index_manager = infra.index_manager
        self._cache_manager = infra.cache_manager
        self._image_store = getattr(infra, "image_store", None)
        self._tenant_id = getattr(infra.settings, "DEFAULT_TENANT_ID", "default")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_document(self, file_path: str, tenant_id: str = "default", kb_id: str = "") -> int:
        """导入文档，返回 chunk 数量

        Args:
            file_path: 文档文件路径
            tenant_id: 租户 ID（用于 ES 索引隔离）
            kb_id: 知识库 ID（可选）

        Returns:
            处理的 chunk 数量
        """
        source = os.path.basename(file_path)
        chunks, precomputed_embeddings = self._document_processor.process_file(file_path)

        if not chunks:
            return 0

        # 确保使用正确的租户索引
        if hasattr(self._doc_store, '_tenant_id'):
            if self._doc_store._tenant_id != tenant_id:
                self._doc_store._tenant_id = tenant_id
                self._doc_store._ensure_index()
                logger.info("Switched ES index to tenant: %s", tenant_id)

        # ---- LLM 增强（可选）----
        config = self._infra.settings
        llm_client = getattr(self._infra, 'llm_client', None)
        enrichment_cache = None

        if llm_client and any([
            getattr(config, 'ENABLE_AUTO_KEYWORDS', False),
            getattr(config, 'ENABLE_AUTO_QUESTIONS', False),
            getattr(config, 'ENABLE_METADATA_EXTRACTION', False),
            getattr(config, 'ENABLE_TOC_EXTRACTION', False),
            getattr(config, 'ENABLE_RAPTOR', False),
            getattr(config, 'ENABLE_CONTENT_TAGGING', False),
        ]):
            from core.enrichment.cache import LLMCache
            import redis as redis_lib
            try:
                redis_url = getattr(config, 'REDIS_URL', '')
                if redis_url:
                    r = redis_lib.from_url(redis_url, decode_responses=True)
                    enrichment_cache = LLMCache(r, ttl=getattr(config, 'ENRICHMENT_CACHE_TTL', 86400))
                else:
                    enrichment_cache = LLMCache(None)
            except Exception:
                enrichment_cache = LLMCache(None)

        if enrichment_cache and llm_client:
            # 自动关键词
            if getattr(config, 'ENABLE_AUTO_KEYWORDS', False):
                try:
                    from core.enrichment.keyword_extractor import KeywordExtractor
                    chunks = KeywordExtractor(
                        llm_client, enrichment_cache,
                        topn=getattr(config, 'AUTO_KEYWORDS_TOPN', 5)
                    ).extract(chunks)
                    logger.info("Auto-keywords extracted for %s", source)
                except Exception as e:
                    logger.warning("Auto-keywords failed for %s: %s", source, e)

            # 自动问题
            if getattr(config, 'ENABLE_AUTO_QUESTIONS', False):
                try:
                    from core.enrichment.question_generator import QuestionGenerator
                    chunks = QuestionGenerator(
                        llm_client, enrichment_cache,
                        topn=getattr(config, 'AUTO_QUESTIONS_TOPN', 3)
                    ).generate(chunks)
                    logger.info("Auto-questions generated for %s", source)
                except Exception as e:
                    logger.warning("Auto-questions failed for %s: %s", source, e)

            # 结构化元数据
            if getattr(config, 'ENABLE_METADATA_EXTRACTION', False):
                try:
                    from core.enrichment.metadata_extractor import MetadataExtractor
                    chunks = MetadataExtractor(llm_client, enrichment_cache).extract(chunks)
                    logger.info("Metadata extracted for %s", source)
                except Exception as e:
                    logger.warning("Metadata extraction failed for %s: %s", source, e)

            # TOC 提取
            if getattr(config, 'ENABLE_TOC_EXTRACTION', False):
                try:
                    from core.enrichment.toc_builder import TOCBuilder
                    toc = TOCBuilder(llm_client, enrichment_cache).build(source, chunks)
                    if toc:
                        logger.info("TOC built for %s: %d entries", source, len(toc.get('items', [])))
                except Exception as e:
                    logger.warning("TOC extraction failed for %s: %s", source, e)

            # RAPTOR
            if getattr(config, 'ENABLE_RAPTOR', False):
                try:
                    from core.enrichment.raptor import RAPTORProcessor
                    embedding_service = getattr(self._infra, 'embedding_service', None)
                    if embedding_service:
                        raptor = RAPTORProcessor(
                            llm_bundle=llm_client,
                            embedding_bundle=embedding_service,
                            cache=enrichment_cache,
                            max_cluster=getattr(config, 'RAPTOR_MAX_CLUSTERS', 64),
                            threshold=getattr(config, 'RAPTOR_THRESHOLD', 0.1),
                            clustering_method=getattr(config, 'RAPTOR_CLUSTERING_METHOD', 'gmm'),
                            small_layer_collapse=getattr(config, 'RAPTOR_SMALL_LAYER_COLLAPSE', 8),
                            max_errors=getattr(config, 'RAPTOR_MAX_ERRORS', 3),
                            max_depth=getattr(config, 'RAPTOR_MAX_DEPTH', 3),
                        )
                        summaries = raptor.process(chunks, source)
                        if summaries:
                            chunks.extend(summaries)
                            logger.info("RAPTOR: added %d summary chunks for %s", len(summaries), source)
                except Exception as e:
                    logger.warning("RAPTOR failed for %s: %s", source, e)

            # Content Tagging
            if getattr(config, 'ENABLE_CONTENT_TAGGING', False):
                try:
                    from core.enrichment.content_tagger import ContentTagger
                    from core.tag_kb import TagKBManager
                    tag_kb_ids_str = getattr(config, 'CONTENT_TAG_KB_IDS', '')
                    tag_kb_ids = [x.strip() for x in tag_kb_ids_str.split(',') if x.strip()]
                    if tag_kb_ids:
                        tag_kb_mgr = TagKBManager(self._doc_store)
                        chunks = ContentTagger(
                            llm_client, enrichment_cache, tag_kb_mgr,
                            topn=getattr(config, 'CONTENT_TAG_TOPN', 3)
                        ).tag(chunks, tag_kb_ids)
                        logger.info("Content tagging done for %s", source)
                except Exception as e:
                    logger.warning("Content tagging failed for %s: %s", source, e)

            # GraphRAG
            if getattr(config, 'GRAPHRAG_ENABLED', False):
                try:
                    self._run_graphrag(chunks, source, config)
                except Exception as e:
                    logger.warning("GraphRAG failed for %s: %s", source, e)

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # 复用语义分块时的 embedding（均值池化），仅编码缺失部分
        embeddings: list[list[float]] = []
        missing_idx: list[int] = []
        for i, emb in enumerate(precomputed_embeddings):
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append([])  # 占位
                missing_idx.append(i)

        if missing_idx:
            missing_texts = [texts[i] for i in missing_idx]
            missing_embs = self._embedding_service.encode(missing_texts)
            for i, emb in zip(missing_idx, missing_embs):
                embeddings[i] = emb

        # 构建 ES 写入行（jieba 预分词）
        rows = []
        chunk_ids = []
        for text, emb, meta in zip(texts, embeddings, metadatas):
            cid = str(uuid.uuid4())
            chunk_ids.append(cid)
            meta["chunk_id"] = cid
            rows.append({
                "id": cid,
                "text": self._doc_store._tokenize(text),  # jieba 分词后存入 text 字段
                "text_raw": text,                          # 原始文本存入 text_raw
                "embedding": emb,
                "source": meta.get("source", source),
                "chunk_id": cid,
                "metadata": meta,
                "tenant_id": tenant_id,
                "kb_id": kb_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        errors = self._doc_store.insert(rows)
        if errors:
            logger.warning("Insert errors for %s: %s", source, errors)

        # KG extraction + ingest
        graph_store = getattr(self._infra, "graph_store", None)
        kg_extractor = getattr(self._infra, "kg_extractor", None)
        if graph_store and kg_extractor:
            import asyncio
            for chunk, meta, cid in zip(chunks, metadatas, chunk_ids):
                try:
                    entities = asyncio.run(kg_extractor.extract_entities(chunk["text"]))
                    relations = asyncio.run(kg_extractor.extract_relations(chunk["text"], entities))
                    graph_store.ingest(cid, source, entities, relations)
                except Exception as e:
                    logger.warning("KG extraction failed for chunk in %s: %s", source, e)

        return len(chunks)

    def _run_graphrag(self, chunks: list[dict], source: str, config):
        """GraphRAG 摄入流水线：提取 → 合并 → 写入 → 消歧 → 社区 → PageRank"""
        from core.kg.merger import GraphMerger
        from core.kg.entity_resolution import EntityResolver
        from core.kg.community import CommunityDetector

        graph_store = getattr(self._infra, 'graph_store', None)
        if not graph_store:
            logger.debug("GraphRAG: no graph store configured")
            return

        llm = getattr(self._infra, 'llm_client', None)
        if not llm:
            return

        # 1. 选择提取后端
        method = getattr(config, 'GRAPHRAG_METHOD', 'general')
        entity_types = config.graphrag_entity_types

        if method == "general":
            from core.kg.extractors.general_extractor import GeneralExtractor
            extractor = GeneralExtractor(
                llm, entity_types=entity_types,
                max_gleanings=getattr(config, 'GRAPHRAG_MAX_GLEANINGS', 2)
            )
        elif method == "light":
            from core.kg.extractors.light_extractor import LightExtractor
            extractor = LightExtractor(llm, entity_types=entity_types)
        elif method == "ner":
            from core.kg.extractors.ner_extractor import NERExtractor
            extractor = NERExtractor()
        else:
            logger.warning("Unknown GraphRAG method: %s", method)
            return

        # 2. 提取
        entities, relations = extractor.extract(chunks)
        if not entities:
            logger.info("GraphRAG: no entities extracted from %s", source)
            return

        logger.info("GraphRAG: extracted %d entities, %d relations from %s",
                     len(entities), len(relations), source)

        # 3. 合并
        merger = GraphMerger()
        entities = merger.merge_entities(entities, llm)
        relations = merger.merge_relations(relations)
        relations = merger.validate_relations(relations)

        logger.info("GraphRAG: after merge: %d entities, %d relations",
                     len(entities), len(relations))

        # 4. 写入 Neo4j
        for ent in entities:
            graph_store.ingest_entity(ent)
        for rel in relations:
            graph_store.ingest_relation(rel)

        # 5. 实体消歧
        if getattr(config, 'GRAPHRAG_ENABLE_RESOLUTION', True):
            try:
                resolver = EntityResolver(llm)
                existing = graph_store.get_all_entities()
                new_ents = [e for e in entities]
                candidates = resolver.find_candidates(new_ents, existing)
                if candidates:
                    confirmed = resolver.confirm_batch(candidates)
                    for new_e, old_e in confirmed:
                        graph_store.merge_entity_nodes(old_e.get("id", ""), new_e.get("id", ""))
                    logger.info("GraphRAG: resolved %d entity pairs", len(confirmed))
            except Exception as e:
                logger.warning("Entity resolution failed: %s", e)

        # 6. 社区检测
        if getattr(config, 'GRAPHRAG_ENABLE_COMMUNITY', True):
            try:
                detector = CommunityDetector(llm)
                G = graph_store.to_networkx()
                communities = detector.detect(G)
                for i, members in enumerate(communities):
                    comm_entities = [G.nodes[n] for n in members if G.has_node(n)]
                    comm_relations = []
                    for u, v in G.edges(members):
                        if G.has_edge(u, v):
                            comm_relations.append(G.edges[u, v])
                    report = detector.generate_report(comm_entities, comm_relations)
                    graph_store.store_community(
                        community_id=f"community_{source}_{i}",
                        members=members,
                        report=report,
                        weight=len(members),
                    )
                logger.info("GraphRAG: detected %d communities", len(communities))
            except Exception as e:
                logger.warning("Community detection failed: %s", e)

        # 7. PageRank
        if getattr(config, 'GRAPHRAG_PAGERANK_ENABLED', True):
            try:
                graph_store.compute_pagerank()
            except Exception as e:
                logger.warning("PageRank computation failed: %s", e)

    def delete_by_source(self, source: str):
        """按来源删除文档（图片 → ES → 缓存）

        为什么先删图片再删 ES：
        ImageStore.cleanup_by_source 需要从 ES metadata 中
        查询该来源的所有 image_path。如果先删了 ES 数据，
        metadata 丢失，图片文件就变成孤儿文件永远留在磁盘上。
        """
        # 1. 先清理图片文件——依赖 ES metadata 定位文件路径
        if self._image_store:
            try:
                self._image_store.cleanup_by_source(source)
            except Exception as e:
                logger.warning("Image cleanup failed for %s: %s", source, e)

        # 2. 再删 ES（此时图片已清理完毕，metadata 可安全丢弃）
        deleted = self._doc_store.delete({"source": source})
        logger.info("Deleted %d chunks for source: %s", deleted, source)

        # 3. 缓存失效——避免检索端命中已删除文档的陈旧结果
        self._cache_manager.invalidate_by_source(source)

        # 4. 清理图谱数据
        graph_store = getattr(self._infra, "graph_store", None)
        if graph_store:
            try:
                graph_store.delete_by_source(source)
            except Exception as e:
                logger.warning("Graph cleanup failed for %s: %s", source, e)

    def delete_all(self):
        """清空所有文档"""
        self._doc_store.delete_idx()
        self._doc_store.create_idx(self._doc_store._index_name, self._doc_store._embedding_dim)
        self._cache_manager.clear()

    def sync_index(self, data_dir: str) -> dict:
        """增量同步索引

        扫描 data_dir 目录，对比已索引文档的 Hash，
        只处理新增、修改、删除的文档。

        Args:
            data_dir: 数据目录路径

        Returns:
            {"added": int, "modified": int, "deleted": int, "unchanged": int}
        """
        changes = self._index_manager.detect_changes(data_dir)
        stats = {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "unchanged": len(changes["unchanged"])
        }

        # 处理删除
        for filename in changes["deleted"]:
            try:
                self.delete_by_source(filename)
                self._index_manager.remove_record(filename)
                stats["deleted"] += 1
                logger.info("Deleted from index: %s", filename)
            except Exception as e:
                logger.warning("Failed to delete %s: %s", filename, e)

        # 处理新增和修改
        for filename in changes["added"] + changes["modified"]:
            file_path = os.path.join(data_dir, filename)
            try:
                # 修改场景：先删旧的
                if filename in changes["modified"]:
                    self.delete_by_source(filename)

                # 索引新文档
                chunks = self.ingest_document(file_path)
                file_hash = IndexManager.compute_file_hash(file_path)
                self._index_manager.record_indexed(filename, file_hash, chunks)

                if filename in changes["added"]:
                    stats["added"] += 1
                    logger.info("Added to index: %s (%d chunks)", filename, chunks)
                else:
                    stats["modified"] += 1
                    logger.info("Updated index: %s (%d chunks)", filename, chunks)
            except Exception as e:
                logger.warning("Failed to index %s: %s", filename, e)

        logger.info("Sync completed: %s", stats)
        return stats

    def get_index_stats(self) -> dict:
        """获取索引统计信息"""
        return {
            "indexed_documents": self._index_manager.get_record_count(),
            "vector_count": self._doc_store.get_document_count(),
        }

    def close(self):
        """释放资源（当前无需特殊清理）。"""
        pass
