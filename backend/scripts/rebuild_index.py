"""重建或增量更新向量库和 BM25 索引

扫描 data/knowledge-base/ 目录下所有文档，重新切块、编码、入库。

用法：
    python rebuild_index.py              # 全量重建（清空旧索引）
    python rebuild_index.py --incremental  # 增量更新（只处理变更）
"""

import os
import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

os.chdir(project_root)

from core.config import config
from core.rag_engine import RAGEngine


def full_rebuild(engine, data_dir):
    """全量重建索引"""
    # 清空旧数据
    engine.delete_all()
    print("已清空旧索引")

    if not os.path.exists(data_dir):
        print(f"数据目录不存在: {data_dir}")
        return

    files = [f for f in os.listdir(data_dir)
             if f.endswith((".md", ".txt", ".html", ".pdf", ".docx", ".png", ".jpg", ".jpeg"))]

    print(f"\n扫描到 {len(files)} 个文件")

    total_chunks = 0
    for i, f in enumerate(files):
        path = os.path.join(data_dir, f)
        try:
            chunks = engine.ingest_document(path)
            total_chunks += chunks
            print(f"  [{i+1}/{len(files)}] {f}: {chunks} chunks")
        except Exception as e:
            print(f"  [{i+1}/{len(files)}] {f}: 失败 ({e})")

    print(f"\n{'='*40}")
    print(f"重建完成!")
    print(f"  文件数: {len(files)}")
    print(f"  总 chunk: {total_chunks}")
    print(f"  向量库: {engine.vector_store.get_document_count()} docs")
    print(f"  BM25: {len(engine.bm25_retriever.doc_ids)} docs")
    print(f"{'='*40}")


def incremental_update(engine, data_dir):
    """增量更新索引"""
    if not os.path.exists(data_dir):
        print(f"数据目录不存在: {data_dir}")
        return

    print("开始增量同步...")
    result = engine.sync_index(data_dir)

    print(f"\n{'='*40}")
    print(f"增量同步完成!")
    print(f"  新增: {result['added']} 个文件")
    print(f"  修改: {result['modified']} 个文件")
    print(f"  删除: {result['deleted']} 个文件")
    print(f"  未变: {result['unchanged']} 个文件")
    print(f"  向量库: {engine.vector_store.get_document_count()} docs")
    print(f"{'='*40}")


def main():
    parser = argparse.ArgumentParser(description="重建或增量更新索引")
    parser.add_argument("--incremental", "-i", action="store_true",
                        help="增量更新模式（只处理变更的文件）")
    args = parser.parse_args()

    print("初始化 RAG 引擎...")
    engine = RAGEngine(config)

    data_dir = config.DATA_DIR

    if args.incremental:
        incremental_update(engine, data_dir)
    else:
        full_rebuild(engine, data_dir)


if __name__ == "__main__":
    main()
