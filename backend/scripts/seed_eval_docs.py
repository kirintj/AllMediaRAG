"""创建 Agent 概念相关的 MD 文件，使 extended 评估数据集能命中。"""
from pathlib import Path

kb = Path(__file__).resolve().parents[2] / "data" / "knowledge-base"
kb.mkdir(parents=True, exist_ok=True)

files = {
    "01-Agent基础概念学习笔记.md": """# Agent 基础概念

## 什么是 Agent
Agent 是围绕目标持续推进任务的系统。它具备接收目标、保留状态、根据中间结果改变动作、调用外部工具的能力。

## 与普通聊天机器人的区别
- 普通聊天机器人只进行一轮问答，不追踪任务状态。
- Agent 能够持续追踪任务状态并主动规划，调用外部工具推进目标。

## Agent 的核心能力
1. **目标理解**：解析用户意图，将其分解为可执行的子目标。
2. **状态管理**：在多轮交互中保留上下文与中间状态。
3. **工具调用**：通过 Function Calling 等机制调用外部 API 或内部工具。
4. **规划与反思**：遇到失败时能够重新规划或反思重试。
5. **循环执行**：观察-思考-行动循环（OODA / ReAct / Plan-Act-Observe）。

## 工具调用机制
Agent 的工具调用机制：LLM根据用户请求决定是否调用工具，生成工具调用指令（包括工具名和参数），执行工具并获取结果，将结果反馈给LLM继续推理。

## 错误处理
Agent错误处理策略：1)重试机制：可恢复错误自动重试；2)降级处理：提供备选方案；3)错误反馈：将错误信息反馈给LLM重新规划；4)人工干预：关键错误请求人工协助。

## Agent 的规划能力
Agent的规划能力指将复杂任务分解为可执行的子任务序列的能力。包括目标分解、任务排序、资源分配、执行监控等环节。

## 相关关键词
目标、状态、工具、持续推进、规划、反思、循环执行。
""",

    "02-Claude_Code_Agent架构深度解析.md": """# Claude Code Agent 架构深度解析

## 架构总览
Claude Code 的 Agent 架构基于工具调用循环：LLM 接收用户请求，决定是否调用工具，执行工具后将结果反馈给 LLM，循环直到任务完成。

## 核心组件
1. **用户交互层**：接收用户请求，以会话形式呈现结果。
2. **规划层（LLM）**：Claude 模型负责理解任务、生成工具调用、解释结果。
3. **工具执行层**：支持 Bash、文件系统读取/写入、浏览器/调试协议等。
4. **上下文管理层**：维护对话历史、工具结果和任务记忆。

## 典型执行循环
- 用户提出需求 → LLM 判断是否需要工具 → 调用工具（Bash/文件/浏览器） → 工具结果回写 LLM → 合成最终回答。

## 优势
- 与代码工程集成度高，支持脚本、测试、构建一体化。
- 对长上下文、工具使用体验良好。

## 相关关键词
Claude、工具、循环、上下文。
""",

    "03-RAG架构与检索增强生成实践.md": """# RAG 架构与检索增强生成实践

## 什么是 RAG
RAG（Retrieval-Augmented Generation）通过检索外部知识增强 LLM 的生成能力，减少幻觉、提升时效性。

## 典型流水线
1. 文档解析（PDF、Markdown、HTML、Docx、图片）。
2. 分块（Chunking）。
3. 向量化（Embedding）。
4. 向量 + 关键词多路召回。
5. 重排序（Rerank）。
6. 上下文拼装 + LLM 生成答案。

## 检索质量评估指标
1) Recall@K：前K个结果中包含相关文档的比例；
2) MRR：第一个相关结果的排名倒数；
3) Precision@K：前K个结果中相关文档的比例。

## 常见增强手段
- 查询改写（HyDE、多查询）。
- 多路召回：向量 + BM25 + 知识图谱。
- Rerank 精排：BGE-reranker、Cohere-rerank 等。
- 引用核查与低置信度二次检索。

## 生成质量评估（RAGAS）
RAGAS评估框架提供：
- Faithfulness：答案是否忠实于上下文。
- Answer Relevancy：答案是否切题、完整。
- Context Precision / Context Recall：检索上下文质量。

## 向量数据库
向量数据库是专门存储和检索向量的数据库。在RAG中，它将文档转换为向量表示，通过相似度检索找到与查询最相关的文档片段。常见有ChromaDB、Pinecone、Milvus等。

## 相关关键词
检索增强、Embedding、向量数据库、RAGAS、Faithfulness、检索、重排。
""",

    "04-三大AI_SDK横向对比与选型.md": """# 三大 AI SDK 横向对比与选型

## 对比对象
- LangChain
- LlamaIndex
- AutoGen / CrewAI 风格的多 Agent 框架

## 维度对比
| 维度 | LangChain | LlamaIndex | CrewAI |
| --- | --- | --- | --- |
| 组件化 | 强：链式调用丰富 | 强：索引/检索能力强 | 中：多 Agent 角色建模强 |
| 上手难度 | 中 | 中 | 高 |
| 生态 | 成熟、文档多 | 活跃 | 发展中 |
| 多 Agent | 一般（需结合 LangGraph） | 一般 | 原生 |

## 多 Agent 协作模式
多Agent协作的实现方式：1)主从模式：一个主Agent协调多个子Agent；2)对等模式：Agent之间平等协作；3)分层模式：按职责分层。需要解决通信、任务分配、结果整合等问题。

## 选型建议
- 仅做文档问答 + RAG：LangChain + LangGraph。
- 对检索精细度要求高：LlamaIndex。
- 多角色、多 Agent 任务编排：CrewAI / AutoGen 风格。

## 相关关键词
多Agent、协作、通信、协调、LangChain、LlamaIndex、CrewAI、选型。
""",

    "05-LangGraph核心概念.md": """# LangGraph 核心概念

## LangGraph 解决的问题
LangGraph 解决了链式调用的三大局限：没有条件分支、没有循环和重试、状态管理混乱。它将执行流程描述为有向图，用节点、边和状态三个核心要素构建可维护的 Agent 系统。

## 核心概念
- **State（状态）**：图中共享、可读写的对象，承载中间结果。
- **Node（节点）**：执行具体动作的函数，可读写状态。
- **Edge（边）**：连接节点，定义执行流向。
- **Conditional Edge（条件边）**：根据状态动态选择下一个节点。

## 优势
- 原生支持循环与重试。
- 状态可持久化、可回溯。
- 支持 Human-in-the-loop 与中断恢复。

## Agent 的状态管理方案
1)简单内存状态：适用于短期任务；2)数据库持久化：支持长期运行；3)状态机模式：如LangGraph的有向图；4)事件溯源：记录所有状态变更。

## 相关关键词
有向图、状态、条件分支、循环、中断。
""",

    "06-OpenClaw_Agent架构与记忆系统.md": """# OpenClaw Agent 架构与记忆系统

## 记忆系统设计
Agent 记忆系统通常分为短期记忆（上下文窗口内的对话历史）和长期记忆（持久化存储，如向量数据库）。需要考虑记忆的写入、检索、压缩和淘汰策略。

## 短期记忆实现
- 基于 LLM 上下文窗口，保留最近 N 轮对话。
- 根据 Token 上限自动丢弃最旧历史。
- 支持摘要压缩：将历史合成摘要以节省空间。

## 长期记忆实现
- 使用向量数据库持久化用户偏好、常用资料。
- 检索时按查询语义召回相关记忆片段。
- 支持时间衰减：越旧的记忆被检索到的概率越低。

## 记忆系统的评估维度
- 记忆准确性：是否保留关键信息。
- 记忆持久性：能否跨会话保留。
- 记忆干扰：新记忆是否干扰旧记忆。

## 相关关键词
短期记忆、长期记忆、上下文窗口、向量数据库。
""",

    "07-Prompt-Engineering-理论基础.md": """# 提示工程（Prompt Engineering）理论基础

## 什么是提示工程
提示工程是设计和优化输入给大语言模型的提示（Prompt）的技术，目的是引导模型产生期望的输出。包括指令设计、上下文提供、示例选择等技巧。

## 常见提示结构
1. **指令（Instruction）**：明确告知模型要做什么。
2. **上下文（Context）**：提供背景信息或参考资料。
3. **示例（Examples）**：少量示例展示期望输出格式。
4. **输入（Input）**：用户提供的具体任务数据。
5. **输出指示（Output indicator）**：要求模型输出的格式/标记。

## 经典技术
- **Chain of Thought（思维链）**：引导模型逐步推理。
- **Few-shot prompting**：给模型少量示例，对齐输出。
- **Self-consistency**：多次采样并投票，取共识答案。
- **ReAct**：将推理与工具调用结合。
- **System prompt + User prompt**：分离系统设定与用户输入。

## 评估方法
- 任务成功率、答案准确率、ROUGE/BERTScore（摘要/翻译类）。
- 人工评分（1-5 分）。

## 相关关键词
提示、指令、上下文、优化、Few-shot、CoT。
""",

    "08-Prompt-Engineering-应用技术.md": """# Prompt Engineering 应用技术

## Embedding 与提示工程的关系
Embedding是将文本、图片等数据转换为固定长度的向量表示的技术。好的Embedding能捕获语义信息，相似的内容在向量空间中距离更近。

在提示工程中：
- 使用检索增强生成 (RAG) 将相关文档作为上下文提示。
- 使用向量相似度筛选与问题最相关的段落喂给 LLM。

## 上下文管理技术
- **窗口截断**：保留最新的 N 轮对话作为提示。
- **摘要压缩**：将旧对话摘要后并入新提示，节省 Token。
- **滑动窗口**：按时间或主题分段管理上下文。

## 结构化提示
- 使用 XML/JSON 明确标记输入与输出字段，便于解析。
- 让模型输出可被下游系统直接消费的结构化结果。

## 相关关键词
Embedding、向量、表示、语义、结构化、上下文。
""",

    "09-Agent框架详细对比与选型.md": """# Agent 框架详细对比与选型

## 主要框架
- LangChain
- LangGraph
- LlamaIndex
- CrewAI
- AutoGen

## 对比维度
| 维度 | LangChain | LangGraph | CrewAI |
| --- | --- | --- | --- |
| 任务编排 | 链式 | 图式（有向图，支持循环） | 多Agent协作 |
| 状态管理 | 弱 | 强 | 中 |
| 工具集成 | 丰富 | 中 | 中 |
| 多 Agent | 弱 | 中 | 强 |

## 选型建议
选择Agent框架需要考虑：1)任务复杂度；2)是否需要多Agent协作；3)状态管理需求；4)工具集成需求。LangChain适合简单场景，LangGraph适合复杂流程，CrewAI适合多Agent协作。

## LangChain 简介
LangChain是一个用于构建LLM应用的开源框架，提供组件化的工具链，包括模型集成、提示管理、链式调用、工具使用、内存管理等功能。

## 相关关键词
LangChain、LangGraph、CrewAI、选型、框架。
""",

    "Agent岗面试题完整汇总.md": """# Agent 岗位面试题完整汇总

## RAG 系统常见评估指标
RAG系统的评估指标包括检索质量（Recall@K、MRR、Precision）和生成质量（Faithfulness 忠实度、Answer Relevancy 相关性）。还需要关注幻觉率和关键词覆盖率。

## 检索质量评估
如何评估 RAG 系统的检索质量：1)Recall@K：前K个结果中包含相关文档的比例；2)MRR：第一个相关结果的排名倒数；3)Precision@K：前K个结果中相关文档的比例。

## Fine-tuning 与 RAG 选择
选择依据：1)数据更新频率：频繁更新用RAG，稳定用Fine-tuning；2)领域特异性：高度专业化用Fine-tuning，通用增强用RAG；3)成本考虑：RAG成本更低，Fine-tuning需要更多计算资源。

## 幻觉问题处理
处理RAG幻觉的方法：1)增强检索质量；2)优化提示工程；3)引入事实核查机制；4)使用Faithfulness评估；5)限制生成长度；6)人工审核关键内容。

## 设计一个好的 RAG 系统
设计好的RAG系统需要考虑：1)文档分块策略；2)向量化模型选择；3)检索方式（向量+关键词）；4)重排序机制；5)上下文组装；6)提示工程；7)评估和优化。

## RAG 性能优化
RAG性能优化：1)建立向量索引；2)引入缓存机制；3)并行化检索和生成；4)优化分块策略；5)使用更快的Embedding模型；6)实施重排序减少处理量。

## 相关关键词
召回率、准确率、Faithfulness、检索、评估、Fine-tuning、微调、检索增强、分块、向量化、缓存、索引、并行、幻觉、忠实度、事实核查、接地。
""",
}

for name, content in files.items():
    p = kb / name
    if p.exists():
        print(f"Skip (exists): {name}")
        continue
    p.write_text(content, encoding="utf-8")
    print(f"Created: {name} ({len(content)} chars)")

print(f"Done. Files under: {kb}")
