# LangGraph 核心概念

> 来源：https://onefly.top/zero2Agent/learn-langgraph/
> 7 篇文章，从状态图角度搭建可维护 Agent 系统

---

## 一、为什么需要 LangGraph

### 链式调用（Chain）的三大局限

1. **没有条件分支** — 需要层层嵌套 if-else
2. **没有循环和重试** — 手写 while True 管理状态
3. **状态管理混乱** — 变量传递变成隐式依赖

---

## 二、LangGraph 的核心思路

将执行流程描述为一张**有向图**，由三个核心要素构成：

| 要素 | 说明 |
|------|------|
| **节点（Node）** | 一个操作（函数） |
| **边（Edge）** | 节点之间的转移关系 |
| **状态（State）** | 贯穿整张图的数据容器 |

### 四大优势
1. 条件分支变成路由函数
2. 循环变成图里的环
3. 状态是显式的
4. 可视化便于调试

---

## 三、三个核心概念

### State（状态）
```python
from typing import TypedDict

class AgentState(TypedDict):
    user_input: str
    sentiment: str
    reply: str
```

### Node（节点）
普通 Python 函数，签名为 `(state: State) -> dict`，只需返回需要更新的字段。

```python
def analyze_node(state: AgentState) -> dict:
    text = state["user_input"]
    sentiment = "positive" if "好" in text else "negative"
    return {"sentiment": sentiment}
```

### Graph（图）
```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("analyze", analyze_node)
graph.add_node("reply", reply_node)
graph.set_entry_point("analyze")
graph.add_edge("analyze", "reply")
graph.add_edge("reply", END)
app = graph.compile()

result = app.invoke({"user_input": "今天心情很好"})
```

---

## 四、链式调用 vs LangGraph

| 维度 | 链式调用 | LangGraph |
|------|---------|-----------|
| 分支逻辑 | if-else 散落代码里 | `add_conditional_edges` 集中管理 |
| 循环/重试 | 手写 while | 图里直接连回原节点 |
| 状态管理 | 变量传递，隐式依赖 | TypedDict，显式类型安全 |
| 可维护性 | 越复杂越难改 | 改节点不影响其他节点 |
| 调试 | print | 可视化图结构 |

---

## 五、适用场景判断

### 适合 LangGraph
- 执行流包含条件分支
- 需要循环迭代
- 多 Agent 协作
- 需要 human-in-the-loop
- 需要错误恢复和重试

### 不一定需要
- 单次 LLM 调用
- 固定线性流程
- 非常简单的两步 chain

---

## 六、LangGraph 进阶特性

### 条件分支（add_conditional_edges）
```python
def router(state):
    if state["sentiment"] == "positive":
        return "positive_handler"
    return "negative_handler"

graph.add_conditional_edges("analyze", router, ...)
```

### 并行执行（Fan-out / Fan-in）
多个节点从同一上游出发，并行执行，汇聚到同一下游。并发节点写同一 state 字段会冲突，用 **Reducer 函数** 合并。

### Prompt Chaining
分步生成：步骤1输出作为步骤2输入，适合长文本分段处理。

### 接入 LLM
支持 OpenAI、HuggingFace 等多种模型接入。

---

## 七、面试常问

### LangGraph 的 State 怎么防膨胀？
- **分层 State**：全局只存核心信息，节点内部用局部变量
- **及时清理**：处理完只保留摘要
- **Checkpoint 策略**：定期保存到外部存储

### LangGraph 并发执行怎么做？
1. **Fan-out/Fan-in（静态并行）**
2. **Send API（动态并行）** — 运行时动态创建分支
3. **节点内部 asyncio 并发**

### State Snapshot 机制？
基于 Checkpoint 的确定性状态管理。类比 Git：Checkpoint ≈ Commit，Thread ≈ Branch，回退 ≈ Reset。
