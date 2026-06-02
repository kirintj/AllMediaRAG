# Agent 框架深度对比续：Mastra / Semantic Kernel / Eino / AgentUniverse / Vercel AI SDK / GitAgent / Skills

> 来源：https://onefly.top/zero2Agent/learn-agent-survey/
> 完整覆盖 13 个框架的详细分析

---

## 一、Mastra：TypeScript 原生 Agent 框架

**定位**：面向 TS 开发者的 LangChain 替代方案，特别适合 Next.js 团队。

### 核心概念
- `Agent` — 带工具、记忆、指令的实例
- `Tool` — 用 **Zod schema** 验证参数
- `Workflow` — 有向图工作流
- `Mastra` — 顶层注册中心

### 关键特点
- TypeScript 原生，完整类型安全 + IDE 自动补全
- Zod schema 校验工具参数
- 工作流 + Agent + 记忆 + RAG 一体化
- Next.js / Vercel 生态无缝集成

### 适用场景
TypeScript/Next.js 团队、Web 应用内嵌 Agent、追求类型安全

---

## 二、Semantic Kernel：微软企业级 AI SDK

**定位**：微软官方 SDK，支持 Python/C#/Java，面向企业集成。

### 核心架构
```
Kernel（容器）
├── Services（AI 服务）
├── Plugins（插件集合）
│   ├── Native Functions（原生代码）
│   └── Semantic Functions（Prompt 模板）
├── Planner（自动编排）
└── Memory（向量语义记忆）
```

### Plugin 系统
```python
class WeatherPlugin:
    @kernel_function(name="get_weather", description="获取城市天气")
    def get_weather(self, city: Annotated[str, "城市名"]) -> Annotated[str, "天气"]:
        ...
```

### 关键特点
- `@kernel_function` 装饰器定义可调用函数
- `KernelFunctionFromPrompt` 将 Prompt 包装成函数
- `FunctionChoiceBehavior.Auto()` 启用自动工具选择
- 内置语义记忆（Chroma 向量存储）
- Azure OpenAI 深度集成

### 适用场景
.NET/C# 技术栈、Azure 生态、Plugin 体系管理大量工具

---

## 三、Eino：字节跳动 Go 语言 Agent 框架

**定位**：生产级 Go AI 框架，高性能低延迟。

### 为什么用 Go
- goroutine 天然高并发
- 无 GIL，无解释器开销
- 单二进制部署
- 字节内部系统大量 Go

### 三层架构
```
Component（组件层）：ChatModel / Retriever / Tool / Lambda
编排层：Chain（顺序） / Graph（有向图）
通信层：Stream（原生流式 I/O）
```

### 关键特点
- 流式是一等公民
- `jsonschema` 结构体标签自动生成工具 Schema
- 豆包（字节 LLM）原生集成

### 适用场景
Go 技术栈、高并发 Agent 服务、字节/豆包生态

---

## 四、AgentUniverse：企业级 Agent 平台

**定位**：配置驱动 + PEER 四角色协作模式。

### PEER 模式
| 角色 | 职责 |
|------|------|
| **P**lanning | 拆分子任务 |
| **E**xecuting | 完成子任务 |
| **E**xpressing | 整合结果 |
| **R**eviewing | 检查质量 |

### 配置驱动
Agent/工具/LLM 全部通过 YAML 声明式配置。

### 关键特点
- PEER 多 Agent 协作
- YAML 配置文件驱动
- 内置可观测性（Tracing）
- 企业知识库接入

### 适用场景
企业复杂分析任务、需要标准化可审计的部署

---

## 五、Vercel AI SDK：全栈 AI 应用框架

**定位**：TypeScript 全栈开发者的 AI 框架，流式优先。

### 三层架构
| 层 | 说明 |
|---|---|
| AI SDK Core | `generateText` / `streamText` / `generateObject` |
| AI SDK UI | `useChat` / `useCompletion` hooks |
| AI SDK RSC | React Server Components |

### 关键 API
```typescript
// 流式生成
const { textStream } = await streamText({ model, prompt });

// 结构化输出
const { object } = await generateObject({ model, schema: z.object({...}), prompt });

// 工具调用（maxSteps 控制自动循环）
const { text } = await generateText({ model, tools, maxSteps: 5, prompt });
```

### 中间件
```typescript
const model = wrapLanguageModel({
  model: openai("o3-mini"),
  middleware: extractReasoningMiddleware({ tagName: "think" }),
});
```

### 适用场景
Next.js 全栈应用、流式 UX、多模型 A/B 测试

---

## 六、GitAgent：代码仓库智能操作

**定位**：工程模式而非框架——将 LLM 接入 Git/GitHub 工作流。

### 五大工具类别
1. 仓库读取（读文件、列目录、搜索、git log）
2. 代码修改（写文件、创建/删除）
3. Git 操作（commit、branch、diff）
4. GitHub API（创建 PR、评论 Issue）
5. 代码执行（运行测试）

### 安全设计
- 命令白名单限制
- 输出截断（工具结果 2000 字符、diff 8000 字符）
- 先读后写策略

### 成熟工具参考
Aider、SWE-agent、OpenHands、GitHub Copilot Workspace

---

## 七、Skills + Claude Code：模块化技能系统

**定位**：按需加载的领域知识机制。

### Skill 文件结构
```yaml
---
name: code-review
description: 帮助进行代码审查。当用户提到"审查代码"时使用。
---
（正文：审查维度、输出格式等指令）
```

### 设计原则
1. 单一职责
2. 触发词明确
3. 可执行指令（祈使句）
4. 控制长度（300-500 行）

### 关键实现
匹配阶段用 Haiku（便宜快速），执行阶段用 Opus（高质量）。

---

## 框架全景选型表

| 场景 | 推荐框架 |
|------|---------|
| 学习底层原理 | **手搓 Agent** |
| RAG 快速原型 | **LangChain** |
| 有状态控制流 | **LangGraph** |
| 多 Agent 对话 | **AutoGen** |
| Deep Research | **DeerFlow** |
| Google Cloud | **Google ADK** |
| 分布式多 Agent | **AgentScope** |
| 配置驱动企业级 | **AgentUniverse** |
| .NET/C#/Azure | **Semantic Kernel** |
| Go 高并发 | **Eino** |
| TypeScript/Next.js | **Mastra** 或 **Vercel AI SDK** |
| 代码仓库自动化 | **GitAgent** |
| Claude Code 定制 | **Skills** |
| 精细控制 Tool Use | **Anthropic SDK** |
| 快速原型+多 Agent | **OpenAI Agents SDK** |
