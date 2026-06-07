"""轻量级RAG测试脚本

不加载Embedding模型，仅测试检索和生成逻辑
适用于内存不足的环境
"""

import json
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
backend_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

os.chdir(project_root)


def test_without_embedding():
    """不加载Embedding模型的测试"""

    print("=" * 60)
    print("轻量级RAG测试（不加载Embedding模型）")
    print("=" * 60)

    # 1. 测试配置加载
    print("\n[1] 测试配置加载...")
    try:
        from core.config import config
        print(f"  ✓ 数据目录: {config.DATA_DIR}")
        print(f"  ✓ LLM模型: {config.MIMO_MODEL}")
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        return

    # 2. 测试LLM调用
    print("\n[2] 测试LLM调用...")
    try:
        from core.llm_client import LLMClient
        llm_client = LLMClient(config.MIMO_API_KEY, config.MIMO_API_BASE, config.MIMO_MODEL)

        test_prompt = "请用一句话介绍什么是RAG技术"
        print(f"  测试提示: {test_prompt}")

        response = llm_client.generate(test_prompt)
        print(f"  ✓ LLM响应: {response[:100]}...")
    except Exception as e:
        print(f"  ✗ LLM调用失败: {e}")
        return

    # 3. 测试文档加载
    print("\n[3] 测试文档加载...")
    try:
        data_dir = config.DATA_DIR
        if os.path.exists(data_dir):
            md_files = [f for f in os.listdir(data_dir) if f.endswith('.md')]
            print(f"  ✓ 找到 {len(md_files)} 个Markdown文件")

            # 读取一个示例文件
            if md_files:
                sample_file = os.path.join(data_dir, md_files[0])
                with open(sample_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"  ✓ 示例文件: {md_files[0]} ({len(content)} 字符)")
        else:
            print(f"  ✗ 数据目录不存在: {data_dir}")
            return
    except Exception as e:
        print(f"  ✗ 文档加载失败: {e}")
        return

    # 4. 测试BM25检索
    print("\n[4] 测试BM25检索...")
    try:
        from core.bm25_retriever import BM25Retriever
        import jieba

        bm25 = BM25Retriever()

        # 准备测试文档
        test_docs = [
            {"id": "1", "text": "RAG是检索增强生成技术，结合了检索和生成", "metadata": {"source": "test1.md"}},
            {"id": "2", "text": "LangGraph用于构建有状态的Agent应用", "metadata": {"source": "test2.md"}},
            {"id": "3", "text": "Python装饰器是修改函数行为的语法糖", "metadata": {"source": "test3.md"}},
        ]

        bm25.build_index(test_docs)

        # 测试检索
        query = "什么是RAG"
        results = bm25.search(query, top_k=2)
        print(f"  ✓ 查询: {query}")
        print(f"  ✓ 检索到 {len(results)} 个结果")

        for i, r in enumerate(results):
            print(f"    [{i+1}] {r['text'][:50]}... (score: {r['score']:.3f})")

    except Exception as e:
        print(f"  ✗ BM25检索失败: {e}")
        import traceback
        traceback.print_exc()

    # 5. 测试查询理解模块
    print("\n[5] 测试查询理解模块...")
    try:
        from core.query_understanding.classifier import QueryClassifier
        from core.query_understanding.router import QueryRouter

        # 测试路由器
        router = QueryRouter()

        test_cases = [
            ("Python装饰器怎么用？", {"intent_type": "factoid", "complexity": "simple"}),
            ("比较RAG和Fine-tuning的优缺点", {"intent_type": "analytical", "complexity": "hard"}),
        ]

        for query, intent in test_cases:
            config_result = router.route(query, intent)
            print(f"  ✓ 查询: {query}")
            print(f"    意图: {intent['intent_type']}, 复杂度: {intent['complexity']}")
            print(f"    推荐配置: use_hyde={config_result['use_hyde']}, top_k={config_result['rerank_top_k']}")

    except Exception as e:
        print(f"  ✗ 查询理解测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 6. 测试缓存系统
    print("\n[6] 测试缓存系统...")
    try:
        from core.performance.cache.l1_cache import L1Cache

        cache = L1Cache(max_size=100, ttl=60)

        # 测试缓存操作
        cache.set("test_key", {"data": "test_value"})
        result = cache.get("test_key")

        if result and result["data"] == "test_value":
            print("  ✓ 缓存写入/读取成功")
        else:
            print("  ✗ 缓存读取失败")

        # 测试缓存过期
        cache.set("expire_key", "value", ttl=1)
        import time
        time.sleep(1.1)
        expired_result = cache.get("expire_key")

        if expired_result is None:
            print("  ✓ 缓存过期机制正常")
        else:
            print("  ✗ 缓存过期机制异常")

    except Exception as e:
        print(f"  ✗ 缓存测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("轻量级测试完成！")
    print("\n要运行完整RAG评估，请：")
    print("1. 增加Windows虚拟内存（4-8GB）")
    print("2. 然后运行: python backend/eval/run_eval.py --dataset extended")
    print("=" * 60)


if __name__ == "__main__":
    test_without_embedding()
