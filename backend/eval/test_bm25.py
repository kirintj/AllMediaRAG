"""BM25检索效果测试

不需要加载Embedding模型，仅测试关键词检索
"""

import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'backend'))
os.chdir(project_root)

from core.bm25_retriever import BM25Retriever


def load_documents(data_dir: str, max_docs: int = 10):
    """加载文档"""
    docs = []
    md_files = [f for f in os.listdir(data_dir) if f.endswith('.md')][:max_docs]

    for i, filename in enumerate(md_files):
        filepath = os.path.join(data_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 简单分块（每500字符一块）
        chunk_size = 500
        for j in range(0, len(content), chunk_size):
            chunk = content[j:j+chunk_size]
            if len(chunk) > 50:  # 忽略太短的块
                docs.append({
                    "id": f"{i}_{j}",
                    "text": chunk,
                    "metadata": {"source": filename}
                })

    return docs


def test_bm25_retrieval():
    """测试BM25检索效果"""

    print("=" * 60)
    print("BM25检索效果测试")
    print("=" * 60)

    # 加载文档
    data_dir = './data/python-docs'
    print(f"\n[1] 加载文档: {data_dir}")

    docs = load_documents(data_dir, max_docs=5)
    print(f"  加载了 {len(docs)} 个文档块")

    # 构建索引
    print("\n[2] 构建BM25索引...")
    bm25 = BM25Retriever()
    bm25.build_index(docs)
    print("  索引构建完成")

    # 测试查询
    test_queries = [
        "什么是Agent？",
        "RAG系统有哪些评估指标？",
        "LangGraph解决了什么问题？",
        "Agent的记忆系统怎么设计？",
        "如何选择合适的Agent框架？"
    ]

    print("\n[3] 测试检索效果...")
    print("-" * 60)

    for query in test_queries:
        print(f"\n查询: {query}")
        results = bm25.search(query, top_k=3)

        if results:
            print(f"  检索到 {len(results)} 个结果:")
            for i, r in enumerate(results[:3], 1):
                source = r['metadata'].get('source', 'unknown')
                score = r['score']
                text_preview = r['text'][:80].replace('\n', ' ')
                print(f"  [{i}] {source} (score: {score:.3f})")
                print(f"      {text_preview}...")
        else:
            print("  未检索到结果")

    print("\n" + "=" * 60)
    print("BM25测试完成！")
    print("\n注意: 这是关键词检索测试，不包含向量语义检索。")
    print("要测试完整RAG效果（包含向量检索），需要增加系统内存。")
    print("=" * 60)


if __name__ == "__main__":
    test_bm25_retrieval()
