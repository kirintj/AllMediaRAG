# 三大 AI SDK 横向对比与选型指南

> 来源：https://onefly.top/zero2Agent/learn-sdk-frameworks/04-sdk-comparison/
> OpenAI Agents SDK vs Google Gemini SDK vs Anthropic Claude SDK

---

## 一、API 设计哲学对比

| SDK | 抽象层级 | 特点 |
|-----|---------|------|
| **OpenAI Agents SDK** | 最高 | Agent 对象 + Runner 自动管理循环 |
| **Google Gemini SDK** | 中等 | 客户端直接调用，支持自动/手动 Function Calling |
| **Anthropic Claude SDK** | 最低 | 完全暴露 Messages API，每步都可见 |

---

## 二、Tool Calling 对比（最关键差异）

### OpenAI — 装饰器注册 + 全自动循环
```python
from agents import Agent, Runner, function_tool

@function_tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city}: 晴天 25°C"

agent = Agent(tools=[get_weather], ...)
result = Runner.run_sync(agent, "北京天气")  # 自动处理工具调用循环
```

### Gemini — 两种模式（手动 schema / 自动函数传递）
```python
# 自动模式：docstring 自动变成工具描述
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city}: 晴天"

response = client.models.generate_content(tools=[get_weather], ...)
```

### Anthropic — 完全手动循环
```python
tools = [{"name": "get_weather", "input_schema": {...}}]
while True:
    response = client.messages.create(tools=tools, messages=messages)
    if response.stop_reason == "tool_use":
        # 手动执行工具，构造 tool_result，追加到 messages
        ...
    else:
        return response.content[0].text
```

### 汇总表

| 维度 | OpenAI | Gemini | Anthropic |
|------|--------|--------|-----------|
| 工具注册 | `@function_tool` 装饰器 | 手动或传函数 | 手动 JSON schema |
| 循环控制 | 全自动（Runner） | 可自动可手动 | 完全手动 |
| 调试难度 | 较难（黑盒） | 中等 | **最容易**（完全透明） |
| 适合场景 | 快速开发 | 灵活中间层 | 生产/精细控制 |

---

## 三、多 Agent 支持

| 维度 | OpenAI | Gemini | Anthropic |
|------|--------|--------|-----------|
| 原生多 Agent | **Handoff 原生支持** | 需自己实现 | 需自己实现 |
| Agent 间通信 | 自动传递对话历史 | 手动管理 | 手动管理 |

OpenAI 的 `handoffs` 是三家中**唯一在 SDK 层面原生支持多 Agent** 的能力。

---

## 四、多模态能力

| 能力 | GPT-4o | Gemini 2.0 | Claude 3.5+ |
|------|--------|------------|-------------|
| 图片输入 | ✅ | ✅ | ✅ |
| 音频输入 | ✅ | ✅ 原生 | ❌ |
| 视频输入 | ❌ | ✅ | ❌ |
| PDF | ❌ | ✅ | ✅ |

**Gemini 在多模态覆盖面上最广**。

---

## 五、定价参考

| 模型 | 输入价格/1M | 输出价格/1M | 定位 |
|------|-----------|-----------|------|
| Gemini Flash | $0.075 | $0.30 | **最便宜** |
| GPT-4o mini | $0.15 | $0.60 | OpenAI 最便宜 |
| Claude Haiku | $0.25 | $1.25 | Claude 最便宜 |
| GPT-4o | $2.50 | $10 | OpenAI 主力 |
| Gemini Pro | $1.25 | $5 | Gemini 主力 |
| Claude Sonnet | $3 | $15 | Claude 主力 |
| Claude Opus | $15 | $75 | 最强但最贵 |

---

## 六、选型决策框架

### 选 OpenAI Agents SDK
- 需要原生多 Agent Handoff
- 快速搭原型
- 典型：客服机器人、多专家协作

### 选 Google Gemini SDK
- 超长文档（100K+ token）
- 视频/音频多模态
- Google Search Grounding
- 典型：文档分析、多媒体处理

### 选 Anthropic Claude SDK
- 精细控制 Tool Use 每一步
- 复杂推理（Extended Thinking）
- 生产高可靠性
- 典型：代码助手、决策系统

---

## 七、学习路径建议

> **学习阶段**优先用 Anthropic SDK——每步都暴露，能看到完整循环。理解手动循环后再看 OpenAI 的自动 Runner，就明白背后做了什么。

> **生产阶段**根据任务需求选模型、根据团队熟悉度选 SDK。

### 生产架构最佳实践
```
外层框架（LangGraph / 自定义）
  ├── 任务A → Claude（复杂推理）
  ├── 任务B → Gemini（长文档处理）
  └── 任务C → GPT-4o（通用对话）
```

**核心原则**：业务逻辑在框架层，LLM 调用封装成统一接口，切换模型只改配置。
