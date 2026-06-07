---
title: 语义相似度切分（Semantic Chunking）设计文档
date: 2026-06-02
status: approved
---

# 语义相似度切分设计

## 背景

当前 RAG 系统使用固定 512 字符 + 50 重叠的段落切分，存在两个问题：
1. 代码块会被截断，导致检索到的代码片段不完整
2. 切分点不考虑语义，可能把一个完整概念拆成两半

需要改为语义相似度切分：用 embedding 计算相邻句子的余弦相似度，相似度骤降处就是语义边界。

## 原理

```
句子序列: [s1, s2, s3, s4, s5, s6, s7, s8]
余弦相似度:   0.9  0.85 0.3  0.8  0.9  0.4  0.85
                              ↑              ↑
                           切分点         切分点
结果: [s1-s3] [s4-s6] [s7-s8]
```

## 改动文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/core/document_processor.py` | 重写 | 加入语义切分逻辑 |
| `backend/core/rag_engine.py` | 不改动 | chunk 输出格式兼容，无需适配 |

## 详细设计

### DocumentProcessor 改动

核心方法变化：

1. `split_into_sentences(text) -> list[str]` — 新增，句子切分
2. `semantic_chunk(sentences, embeddings) -> list[list[int]]` — 新增，基于相似度切分
3. `process_document(html_content, source) -> list[dict]` — 重写，使用语义切分
4. `process_file(file_path) -> list[dict]` — 不变

### 句子切分规则

- 按中文句号（。）、问号（？）、感叹号（！）、换行符切分
- 代码块（` ``` ` 包裹）作为整体，内部不拆分
- 连续空白行视为段落分隔

### 语义切分算法

```python
def semantic_chunk(self, sentences: list[str], embeddings: list) -> list[list[int]]:
    # 1. 计算相邻句子的余弦相似度
    similarities = []
    for i in range(len(embeddings) - 1):
        sim = cosine_similarity(embeddings[i], embeddings[i + 1])
        similarities.append(sim)

    # 2. 动态阈值：取 25 分位数
    threshold = np.percentile(similarities, 25)

    # 3. 低于阈值处切分
    chunks = []
    current_chunk = [0]
    for i, sim in enumerate(similarities):
        if sim < threshold:
            chunks.append(current_chunk)
            current_chunk = [i + 1]
        else:
            current_chunk.append(i + 1)
    chunks.append(current_chunk)

    return chunks
```

### 代码块保护

解析时先用正则提取 ` ``` ` 包裹的代码块，替换为占位符。文本切分完成后，将占位符替换回原代码块。代码块作为整体，不参与句子切分。

### chunk 输出格式

与现有格式兼容，无需改动下游：

```python
{
    "text": "合并后的 chunk 文本",
    "metadata": {
        "source": "文件名",
        "section": "章节标题",
        "chunk_index": 0
    }
}
```

### 配置参数

新增到 `config.py`：

```python
SEMANTIC_CHUNK_PERCENTILE: int = 25    # 相似度阈值百分位
SEMANTIC_CHUNK_MIN_SENTENCES: int = 2  # 每个 chunk 最少句子数
SEMANTIC_CHUNK_MAX_SENTENCES: int = 20 # 每个 chunk 最多句子数
```

## 不改动的部分

- `vector_store.py` — 不变
- `embedding_service.py` — 不变
- `llm_client.py` — 不变
- `bm25_retriever.py` — 不变
- 前端 — 不变
- `api/` — 不变
