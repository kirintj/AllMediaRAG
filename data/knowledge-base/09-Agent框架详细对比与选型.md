# Agent 框架详细对比：手搓/DdeerFlow/LangChain/AutoGen/Google ADK

> 来源：https://onefly.top/zero2Agent/learn-agent-survey/
> 从源码级理解各框架的设计哲学与选型决策

---

## 一、手搓 Agent：从原理到实现

### 核心理念
> 框架本质上就是别人手写的 Agent。只有理解底层原理，框架对你来说才是透明的。

### 最小 Agent（约 200 行）
```python
while True:
    decision = llm(history + system_prompt)
    if decision.wants_tool:
        result = execute_tool(decision.tool_name, decision.args)
        history.append(result)
    else:
        return decision.text
```

### 关键组件
1. **ToolRegistry** — 工具注册（register + 装饰器 + schemas + call）
2. **Agent 核心类** — system_prompt + model + max_iterations + history
3. **stop_reason 判断** — `"tool_use"` 继续循环 / `"end_turn"` 退出
4. **并发工具调用** — `ThreadPoolExecutor` 并行执行

### 框架 vs 手写对应关系

| 框架能力 | 手写代码对应 |
|---------|-------------|
| 工具注册 | `ToolRegistry.register()` |
| 工具调用循环 | `while True` + stop_reason |
| 对话历史管理 | `self.history.append(...)` |
| 最大迭代保护 | `for iteration in range(max_iterations)` |

### 什么时候手搓
1. 学习目的
2. 极简场景
3. 生产可控
4. 性能敏感

---

## 二、DeerFlow：字节 Deep Research 框架

### 四步流程
**规划 → 搜索 → 分析 → 综合**

### 多 Agent 架构
```
[Coordinator] → [Planner] → [Researcher 1..N]（并行）→ [Writer] → 最终报告
```

### 核心代码（LangGraph）
```python
class ResearchState(TypedDict):
    user_input: str
    research_plan: List[str]
    search_results: Annotated[List[str], operator.add]  # Reducer 模式
    final_report: str

graph = StateGraph(ResearchState)
graph.add_node("coordinator", coordinator_node)
graph.add_node("planner", planner_node)
graph.add_node("researcher", researcher_node)
graph.add_node("writer", writer_node)
```

### 关键知识点
- **Reducer 模式**：`Annotated[List[str], operator.add]` 实现多节点结果追加合并
- **搜索+分析两步走**：先检索原始信息，再用 LLM 摘要提炼
- **LLM 分层配置**：区分基础模型和推理模型

---

## 三、LangChain：最流行的 LLM 框架

### 核心演进
- v0.1：Chain 为中心（`LLMChain` + `PromptTemplate`）
- v0.2+：**LCEL** 为中心（管道操作符 `|`）

### LCEL 管道
```python
chain = prompt | llm | StrOutputParser()
```

串行：`step1 | step2`
并行：`RunnableParallel(upper=str.upper, lower=str.lower)`

### RAG 四步流程
```python
# 加载 → 切分 → 向量化 → 检索链
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt | ChatOpenAI() | StrOutputParser()
)
```

### Agent 工具调用
```python
@tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    ...

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

### 四大痛点
1. 过度抽象
2. API 频繁变动
3. 调试困难（stack trace 可读性差）
4. 性能开销

### 与 LangGraph 的关系
> **用 LangGraph 做控制流，用 LangChain 的工具/加载器做周边集成，不要用 LangChain 自带的 Agent 抽象层。**

---

## 四、AutoGen：微软多 Agent 对话框架

### 核心理念
多个 Agent 通过**自然语言对话**协作完成任务。

### 核心概念
| 概念 | 说明 |
|------|------|
| `AssistantAgent` | 调用 LLM 的 Agent |
| `UserProxyAgent` | 代理用户，可执行代码 |
| `RoundRobinGroupChat` | 轮流发言 |
| `SelectorGroupChat` | LLM 动态决定发言顺序 |

### 经典模式：Coder + Executor
```python
coder = AssistantAgent(system_message="写代码...")
executor = CodeExecutorAgent(code_executor=LocalCommandLineCodeExecutor())
team = RoundRobinGroupChat(participants=[coder, executor])
```

### 两种群聊模式
- **RoundRobin**：固定顺序，简单可预测
- **Selector**：LLM 动态路由，灵活但不确定

### 优缺点
**优点**：代码执行原生支持、Human-in-the-loop 完善、多 Agent 对话自然
**缺点**：对话难以预测、版本迁移混乱、不适合精确控制流程

---

## 五、Google ADK：官方 Agent 开发套件

### 核心概念
| 概念 | 说明 |
|------|------|
| `Agent` | 绑定模型+指令+工具 |
| `Tool` | 类型注解自动生成 schema |
| `Runner` | 执行 Agent，管理 Session |
| `MultiAgent` | 多 Agent 编排 |

### 三种多 Agent 编排模式
```python
# 顺序执行
SequentialAgent(sub_agents=[fetch, analyze, report])

# 并行执行
ParallelAgent(sub_agents=[web_search, db_search, api])

# LLM 路由
Agent(sub_agents=[tech_agent, billing_agent, support_agent])
```

### 内置 Google 工具
- `google_search` — Google Search grounding
- `code_execution` — 沙箱 Python 执行

### 适用场景
- Gemini 模型为主
- 需要 Google Search
- Vertex AI 部署

---

## 六、AgentScope：阿里分布式多 Agent 框架

### 三大核心抽象
- `AgentBase` — 基类，重写 `reply()` 方法
- `Msg` — 消息对象（name/role/content）
- `Pipeline` — 流程控制器

### 分布式特性
```python
agent.to_dist()  # 一键分布式，底层 RPC
```

### 适用场景
- 分布式多 Agent
- 国内部署 + 通义千问
- 阿里云生态

---

## 七、框架选型总结

| 场景 | 推荐框架 |
|------|---------|
| 学习底层原理 | **手搓** |
| RAG 快速原型 | **LangChain** |
| 有状态 Agent 控制流 | **LangGraph** |
| 多 Agent 对话协作 | **AutoGen** |
| Deep Research | **DeerFlow** |
| Google Cloud 生态 | **Google ADK** |
| 分布式多 Agent | **AgentScope** |
| 精细控制 Tool Use | **Anthropic SDK** |
| 快速原型 + 多 Agent | **OpenAI Agents SDK** |

> 面试中展示框架选型判断力比"用过某个框架"更有价值。
