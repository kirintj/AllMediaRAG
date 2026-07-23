# GraphRAG 增强设计文档

## 概述

增强 ALLRAG 的知识图谱能力：新增 3 种提取后端（General/Light/NER）、实体合并与验证、实体消歧、Leiden 社区检测、PageRank 计算、N-hop 路径扩展检索。基于现有 Neo4j 基础设施，参照 RAGFlow 的 GraphRAG 实现对齐。

## 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 图数据库 | 继续 Neo4j | 已有基础设施，生产级 |
| 提取后端 | General + Light + NER（3 种） | 与 RAGFlow 一致 |
| 实体合并 | 同名合并 + 类型投票 + 描述摘要 | 与 RAGFlow 一致 |
| 关系验证 | 负面模式过滤 + 主语匹配 | 与 RAGFlow 一致 |
| 实体消歧 | 编辑距离 + LLM 批量确认 | 与 RAGFlow 一致 |
| 社区检测 | Leiden 算法 + LLM 社区报告 | 与 RAGFlow 一致 |
| PageRank | NetworkX 计算，写回 Neo4j | 实体重要性排序 |
| 检索融合 | 独立返回图谱上下文 | LLM 自行判断使用 |

## 架构

```
摄入时：
chunk → 提取器（General/Light/NER）
    → GraphMerger（实体合并 + 关系合并 + 关系验证）
    → 写入 Neo4j
    → EntityResolver（编辑距离 + LLM 消歧）
    → CommunityDetector（Leiden + LLM 报告）
    → PageRank 计算

检索时：
用户问题 → LLM 提取实体名 + 类型
    → Neo4j 实体检索（名称匹配 + pagerank 排序）
    → N-hop 路径扩展
    → 关系检索
    → 社区报告检索
    → 格式化为文本，独立返回
```

## 3 种提取后端

### General Extractor（GraphRAG-style）

- LLM 提取实体（name, type, description）+ 关系（source, target, description, weight）
- 最多 2 轮 gleaning（CONTINUE_PROMPT 追加提取遗漏实体）
- 默认实体类型：organization, person, geo, event, category
- Prompt 与 RAGFlow 的 graph_prompt.py 对齐

### Light Extractor（LightRAG-style）

- 更简洁的 prompt，更少的实体类型
- 无 gleaning 轮次，速度快
- 适合对质量要求不高的场景

### NER Extractor（spaCy）

- 无需 LLM 调用，速度快
- 实体类型由 spaCy 模型决定（PER, ORG, GPE, LOC 等）
- 关系提取通过共现（同一 chunk 中的实体对）

### 统一接口

```python
class BaseExtractor(ABC):
    def extract(self, chunks: list[dict]) -> tuple[list[dict], list[dict]]:
        """返回 (entities, relations)"""
        ...
```

### 实体格式

```python
{"name": "华为", "type": "organization", "description": "全球领先的ICT基础设施", "source_id": "chunk_001"}
```

### 关系格式

```python
{"source": "华为", "target": "深圳", "description": "总部位于", "weight": 1, "keywords": ["总部", "深圳"]}
```

## 实体/关系合并

### 实体合并规则

- 同名实体（case-insensitive）合并
- 类型：多数投票
- 描述：拼接（`<SEP>` 分隔），超过 12 段时 LLM 摘要
- 来源：合并 source_id 集合

### 关系合并规则

- 同对关系（无向）合并
- 权重：叠加
- 描述：拼接
- 关键词：并集

### 关系验证

丢弃以下模式的关系：
- 描述包含 "no clear relationship"、"not directly linked"、"无明确关系"、"无直接关联" 等
- 描述主语与端点实体不匹配

## 实体消歧

```python
class EntityResolver:
    def resolve(self, new_entities: list[dict]):
        # 1. 按类型分组
        # 2. 新实体 vs 已有实体，生成候选对
        # 3. 编辑距离过滤：
        #    - 中文：字符集重叠 ≥ 80%
        #    - 英文：editdistance ≤ 2
        # 4. LLM 批量确认（每批 100 对）
        # 5. 合并确认的重复实体到 Neo4j
```

## 社区检测

```python
class CommunityDetector:
    def detect_and_report(self):
        # 1. 从 Neo4j 导出 NetworkX 图
        # 2. Louvain 社区检测（networkx.algorithms.community）
        # 3. 每个社区：收集实体/关系 → LLM 生成报告
        # 4. 报告存入 Neo4j（community_id, members, report, weight）
```

## PageRank

```python
def compute_pagerank(self):
    """NetworkX 计算 PageRank，写回 Neo4j 节点的 pagerank 属性"""
    G = self.to_networkx()
    pr = nx.pagerank(G, alpha=0.85)
    for node_id, rank in pr.items():
        # MATCH (n {id: $id}) SET n.pagerank = $rank
```

## 检索融合

`GraphRetriever.retrieve(query) -> str | None`：

1. **查询分析**：LLM 从问题提取实体名 + 实体类型
2. **实体检索**：Neo4j 名称匹配 + 类型过滤 + pagerank 排序
3. **N-hop 扩展**：2 跳以内路径（`(start)-[*1..2]-(end)`）
4. **关系检索**：端点包含已匹配实体的关系
5. **社区报告**：成员包含已匹配实体的社区
6. **格式化**：输出文本（实体表 + 关系表 + 路径 + 社区报告）

检索结果独立返回，在 generation_service.py 中作为额外上下文拼接到 prompt。

## Prompt 模板

```
core/kg/prompts/
├── general_extraction.md    # General 提取器 prompt
├── light_extraction.md      # Light 提取器 prompt
├── gleaning_prompt.md       # gleaning 追加提取
├── entity_resolution.md     # 实体消歧确认
├── summarize_descriptions.md # 描述摘要（超长时）
├── community_report.md      # 社区报告生成
└── query_analyze.md         # 查询分析（提取实体名+类型）
```

## 配置

```python
# config.py 新增
GRAPHRAG_ENABLED: bool = False
GRAPHRAG_METHOD: str = "general"  # general / light / ner
GRAPHRAG_ENTITY_TYPES: str = "organization,person,geo,event,category"
GRAPHRAG_MAX_GLEANINGS: int = 2
GRAPHRAG_ENABLE_RESOLUTION: bool = True
GRAPHRAG_ENABLE_COMMUNITY: bool = True
GRAPHRAG_PAGERANK_ENABLED: bool = True
```

## 变更清单

### 新增（~10 个）

- `core/kg/extractors/__init__.py`
- `core/kg/extractors/general_extractor.py`
- `core/kg/extractors/light_extractor.py`
- `core/kg/extractors/ner_extractor.py`
- `core/kg/merger.py`
- `core/kg/entity_resolution.py`
- `core/kg/community.py`
- `core/kg/prompts/*.md`（7 个 prompt 模板）

### 修改（4 个）

- `core/kg/graph_store.py` — 新增 PageRank、N-hop、to_networkx、社区存储
- `core/kg/graph_retriever.py` — 增强检索（查询分析 + N-hop + 社区 + 格式化）
- `core/kg/extractor.py` — 路由到 3 种后端
- `core/services/ingestion_service.py` — 集成合并/消歧/社区/PageRank
- `core/config.py` — 新增配置项
- `core/services/generation_service.py` — 图谱上下文拼接
