"""重建向量库和 BM25 索引

扫描 data/knowledge-base/ 目录下所有文档，重新切块、编码、入库。
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

os.chdir(project_root)

from core.config import config
from core.rag_engine import RAGEngine


def main():
    print("初始化 RAG 引擎...")
    engine = RAGEngine(config)

    # 清空旧数据
    engine.delete_all()
    print("已清空旧索引")

    data_dir = config.DATA_DIR
    if not os.path.exists(data_dir):
        print(f"数据目录不存在: {data_dir}")
        return

    files = [f for f in os.listdir(data_dir)
             if f.endswith((".md", ".txt", ".html", ".pdf", ".docx"))]

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


if __name__ == "__main__":
    main()
