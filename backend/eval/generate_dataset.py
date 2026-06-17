"""LLM 辅助评估数据集生成器

从知识库文档自动生成评估问题，覆盖 查询类型 × 难度 矩阵。
生成后需人工审核质量。

运行方式：
    cd backend && python -m eval.generate_dataset --count 100 --output eval/eval_dataset_auto.json
"""

import json
import sys
import os
import re
import random
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))


QUERY_TYPES = ["factoid", "analytical", "procedural", "exploratory"]
DIFFICULTIES = ["easy", "medium", "hard"]

# 每种类型的模板提示
QUESTION_TEMPLATES = {
    "factoid": {
        "easy": "请根据文档回答一个简单的事实问题：{topic}",
        "medium": "请根据文档回答一个需要综合信息的事实问题：{topic}",
        "hard": "请根据文档回答一个需要跨文档推理的事实问题：{topic}",
    },
    "analytical": {
        "easy": "请分析以下概念的含义：{topic}",
        "medium": "请比较分析以下技术方案的优劣：{topic}",
        "hard": "请深入分析以下架构设计的权衡取舍：{topic}",
    },
    "procedural": {
        "easy": "如何执行以下操作：{topic}",
        "medium": "请描述实现以下功能的步骤：{topic}",
        "hard": "请设计一个完整的实施方案：{topic}",
    },
    "exploratory": {
        "easy": "请介绍一下以下概念：{topic}",
        "medium": "请全面探讨以下技术的应用场景：{topic}",
        "hard": "请综合分析以下领域的最新发展和趋势：{topic}",
    },
}

# 目标分布矩阵
TARGET_MATRIX = {
    ("factoid", "easy"): 10,
    ("factoid", "medium"): 10,
    ("factoid", "hard"): 10,
    ("analytical", "easy"): 8,
    ("analytical", "medium"): 10,
    ("analytical", "hard"): 7,
    ("procedural", "easy"): 8,
    ("procedural", "medium"): 10,
    ("procedural", "hard"): 7,
    ("exploratory", "easy"): 5,
    ("exploratory", "medium"): 5,
    ("exploratory", "hard"): 5,
}


def load_documents(data_dir: str) -> list[dict]:
    """加载知识库文档，返回 [{source, content}, ...]"""
    documents = []
    data_path = Path(data_dir)

    if not data_path.exists():
        print(f"警告: 数据目录不存在: {data_dir}")
        return documents

    for file_path in data_path.iterdir():
        if file_path.suffix.lower() in ('.md', '.txt', '.html', '.htm'):
            try:
                content = file_path.read_text(encoding='utf-8')
                if content.strip():
                    documents.append({
                        "source": file_path.name,
                        "content": content[:5000],  # 限制长度
                    })
            except Exception as e:
                print(f"警告: 读取 {file_path.name} 失败: {e}")

    return documents


def extract_topics(documents: list[dict]) -> list[dict]:
    """从文档中提取主题（基于标题和关键段落）"""
    topics = []

    for doc in documents:
        source = doc["source"]
        content = doc["content"]

        # 提取 Markdown 标题作为主题
        headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
        for heading in headings[:5]:  # 每个文档最多 5 个主题
            topics.append({
                "topic": heading.strip(),
                "source": source,
                "context": content[:500],
            })

        # 如果没有标题，用前 100 字符作为主题
        if not headings and content.strip():
            topics.append({
                "topic": content[:100].split('\n')[0].strip(),
                "source": source,
                "context": content[:500],
            })

    return topics


def generate_question_with_llm(
    llm_client, topic: dict, query_type: str, difficulty: str
) -> dict:
    """使用 LLM 生成一个评估问题

    Args:
        llm_client: LLM 客户端
        topic: {"topic": str, "source": str, "context": str}
        query_type: 查询类型
        difficulty: 难度

    Returns:
        评估样本字典
    """
    prompt = f"""你是一个 RAG 系统评估数据集生成专家。请根据以下文档片段，生成一个评估问题。

## 文档来源
{topic['source']}

## 文档内容
{topic['context'][:1000]}

## 要求
- 查询类型: {query_type}（{QUERY_TYPES.index(query_type) + 1}/4）
- 难度: {difficulty}
- 问题必须能从上述文档中找到答案
- 生成的问题、参考答案和关键词

请以 JSON 格式输出：
{{
    "question": "生成的问题",
    "reference_answer": "基于文档的参考答案",
    "expected_keywords": ["关键词1", "关键词2", "关键词3"]
}}

只输出 JSON，不要其他内容。"""

    try:
        response = llm_client.generate(prompt)
        # 解析 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "question": result.get("question", ""),
                "query_type": query_type,
                "difficulty": difficulty,
                "expected_sources": [topic["source"]],
                "expected_keywords": result.get("expected_keywords", []),
                "reference_answer": result.get("reference_answer", ""),
            }
    except Exception as e:
        print(f"  LLM 生成失败 ({query_type}/{difficulty}): {e}")

    # 降级：使用模板
    template = QUESTION_TEMPLATES[query_type][difficulty]
    return {
        "question": template.format(topic=topic["topic"]),
        "query_type": query_type,
        "difficulty": difficulty,
        "expected_sources": [topic["source"]],
        "expected_keywords": [topic["topic"]],
        "reference_answer": f"请参考 {topic['source']} 中关于 {topic['topic']} 的内容。",
    }


def generate_dataset(
    data_dir: str,
    count: int = 100,
    output_path: str = None,
    use_llm: bool = True,
) -> list[dict]:
    """生成评估数据集

    Args:
        data_dir: 知识库文档目录
        count: 目标问题数量
        output_path: 输出文件路径（可选）
        use_llm: 是否使用 LLM 生成（False 时使用模板）

    Returns:
        评估样本列表
    """
    # 加载文档
    print(f"正在加载文档: {data_dir}")
    documents = load_documents(data_dir)
    if not documents:
        print("错误: 没有找到可用的文档文件")
        return []

    print(f"加载了 {len(documents)} 个文档")

    # 提取主题
    topics = extract_topics(documents)
    print(f"提取了 {len(topics)} 个主题")

    if not topics:
        print("错误: 无法从文档中提取主题")
        return []

    # 初始化 LLM
    llm_client = None
    if use_llm:
        try:
            from core.config import config
            from core.llm_client import LLMClient
            llm_client = LLMClient(
                config.MIMO_API_KEY,
                config.MIMO_API_BASE,
                config.MIMO_MODEL,
            )
            print("LLM 客户端初始化成功")
        except Exception as e:
            print(f"警告: LLM 初始化失败，将使用模板: {e}")

    # 按矩阵生成问题
    dataset = []
    sample_id = 1

    # 计算每个类型需要生成的数量
    total_target = sum(TARGET_MATRIX.values())
    scale = count / total_target if total_target > 0 else 1.0

    for (query_type, difficulty), target_count in TARGET_MATRIX.items():
        actual_count = max(1, round(target_count * scale))

        for i in range(actual_count):
            # 随机选择主题
            topic = random.choice(topics) if topics else {"topic": "通用问题", "source": "unknown", "context": ""}

            if llm_client:
                sample = generate_question_with_llm(
                    llm_client, topic, query_type, difficulty
                )
            else:
                template = QUESTION_TEMPLATES[query_type][difficulty]
                sample = {
                    "question": template.format(topic=topic["topic"]),
                    "query_type": query_type,
                    "difficulty": difficulty,
                    "expected_sources": [topic["source"]],
                    "expected_keywords": [topic["topic"]],
                    "reference_answer": f"请参考 {topic['source']} 中关于 {topic['topic']} 的内容。",
                }

            sample["id"] = sample_id
            dataset.append(sample)
            sample_id += 1

            if sample_id % 10 == 0:
                print(f"  已生成 {sample_id}/{count} 个问题...")

    # 保存
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"\n数据集已保存: {output_path} ({len(dataset)} 个样本)")

    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM 辅助评估数据集生成器")
    parser.add_argument("--data-dir", default="../data/knowledge-base",
                        help="知识库文档目录")
    parser.add_argument("--count", type=int, default=100,
                        help="目标问题数量 (default: 100)")
    parser.add_argument("--output", default="eval/eval_dataset_full.json",
                        help="输出文件路径")
    parser.add_argument("--no-llm", action="store_true",
                        help="不使用 LLM，仅用模板生成")

    args = parser.parse_args()

    dataset = generate_dataset(
        data_dir=args.data_dir,
        count=args.count,
        output_path=args.output,
        use_llm=not args.no_llm,
    )

    if dataset:
        # 打印统计
        by_type = {}
        by_diff = {}
        for s in dataset:
            t = s.get("query_type", "?")
            d = s.get("difficulty", "?")
            by_type[t] = by_type.get(t, 0) + 1
            by_diff[d] = by_diff.get(d, 0) + 1

        print(f"\n统计:")
        print(f"  总数: {len(dataset)}")
        print(f"  按类型: {by_type}")
        print(f"  按难度: {by_diff}")
