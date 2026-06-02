# Agent 框架横向调研索引

> 来源：https://onefly.top/zero2Agent/learn-agent-survey/
> 13 个框架横向调研，建立框架选型判断力

---

## 框架列表

| # | 框架 | 定位 | 关键特点 |
|---|------|------|---------|
| 1 | **AgentScope** | 阿里的多 Agent 框架 | 多 Agent 协作、分布式 |
| 2 | **Mastra** | TypeScript 原生 Agent 框架 | 前端开发者友好 |
| 3 | **Semantic Kernel** | 微软的企业级 AI SDK | C#/Python/Java、企业集成 |
| 4 | **Eino** | 字节跳动的 Go 语言框架 | 高性能、Go 生态 |
| 5 | **GitAgent** | 代码仓库智能操作 | Git 仓库自动化 |
| 6 | **手搓 Agent** | 从原理到实现 | 理解底层机制 |
| 7 | **AgentUniverse** | 华为企业级 Agent 平台 | 企业场景、多 Agent |
| 8 | **DeerFlow** | 字节的 Deep Research 框架 | 深度研究、多步检索 |
| 9 | **LangChain** | 最流行的 LLM 框架 | 生态最大、Chain/Agent 模式 |
| 10 | **Google ADK** | 官方 Agent 开发套件 | Gemini 原生集成 |
| 11 | **Skills + Claude Code** | 模块化技能系统 | Markdown 定义、渐进披露 |
| 12 | **Vercel AI SDK** | 全栈 AI 应用框架 | Next.js 集成、流式 UI |
| 13 | **AutoGen** | 微软的多 Agent 对话框架 | 多 Agent 对话、群聊模式 |

---

## 选型维度

选择框架时关注的核心维度：
1. **语言生态** — Python/TypeScript/Go/Java
2. **抽象层级** — 高层（自动循环）vs 低层（完全控制）
3. **多 Agent 支持** — 原生 vs 需自建
4. **工具集成** — MCP 支持、Function Calling
5. **状态管理** — Checkpoint、持久化
6. **可观测性** — 日志、Trace、调试
7. **社区与生态** — 文档、插件、案例

---

## 面试中的框架对比要点

### LangChain vs LangGraph
- LangChain：链式编排，适合流程固定的 LLM 应用
- LangGraph：有状态图执行，支持条件分支、循环、并行、Checkpoint

### AutoGen vs AgentScope
- AutoGen：多 Agent 对话模式，适合群聊式协作
- AgentScope：分布式多 Agent，适合大规模部署

### 自写 vs 框架
- 框架优势：开箱即用、社区支持
- 框架劣势：黑盒调试难、定制化成本高
- **面试加分点**：能说清为什么选/不选某个框架

---

## 学习建议

> 面试中展示框架选型判断力比"用过某个框架"更有价值。
> 
> 建议至少深入学习 1 个框架（如 LangGraph），了解 2-3 个框架的核心设计，能做横向对比。
