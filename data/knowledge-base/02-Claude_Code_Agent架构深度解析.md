# Claude Code Agent 架构深度解析

> 来源：https://onefly.top/zero2Agent/learn-claude-code/
> 12 篇文章，手写 Coding Agent 全流程

---

## 1. Agent Loop：一个循环就是一个 Agent

### 核心命题
Agent 的本质可以用一个 `while True` 循环概括——不到 30 行 Python 即可构建最小 Agent。

### 基本流程
用户 prompt → LLM → 若 tool_use 则执行工具并将 tool_result 返回 LLM → 循环 → 若 stop 则结束

### 三个关键组件

**Messages 累积机制**：每轮响应和工具结果都**追加**进 messages 列表，模型始终可见完整执行历史。

**stop_reason 作为唯一退出条件**：
| stop_reason | 含义 |
|---|---|
| `"tool_use"` | 要调用工具，继续循环 |
| `"end_turn"` | 完成任务，退出 |
| `"max_tokens"` | 超限，需处理 |

**tool_result 格式要求**：工具结果必须 `tool_use_id` 与对应 tool_use 的 id 匹配。

### 生产级源码（Claude Code）的六种状态转移

| transition.reason | 触发条件 | 恢复策略 |
|---|---|---|
| `next_turn` | 正常工具调用→继续 | 核心路径 |
| `collapse_drain_retry` | prompt-too-long | 折叠历史摘要 |
| `reactive_compact_retry` | 仍过长 | 激进压缩 |
| `max_output_tokens_escalate` | 输出截断 | 8k→64k |
| `max_output_tokens_recovery` | 升级后仍截断 | 注入恢复消息 |
| `stop_hook_blocking` | lint失败 | 注入错误让模型修复 |

### 设计哲学
Agent 公式：**Tool Calls + Context Management + Task Planning + Error Handling + Permission Control + State Persistence = Agent System**

Chatbot → Agent 的关键跃迁：chatbot 在模型说完话时停下，agent 在模型没有更多工具要调用时才停下。

---

## 2. Tool Use：扩展模型能触达的边界

（详见基础概念笔记 Tool Calling 部分）

---

## 3. TodoWrite：让 Agent 不再迷路

### 核心问题
长任务中 Agent 容易"迷路"——忘记已完成什么、接下来做什么。

### 解决方案
维护一个结构化的 to-do list：
- `pending` — 待办
- `in_progress` — 进行中
- `completed` — 已完成

每步执行后更新状态并注入上下文，起到**锚点**作用。

---

## 4. Subagent：上下文隔离的正确姿势

### 核心价值
Subagent 的本质是**上下文管理策略**——子进程做脏活，父进程只看结果。

### 适用场景
1. 子任务产生大量中间结果，主任务只需最终结论
2. 子任务上下文与主任务高度不相关
3. 需要并行处理多个独立子任务

### 关键设计
主 Agent 和子 Agent **不共用上下文**，通过结构化消息通信：
- 主→子：子任务描述 + 必要上下文
- 子→主：执行结论 + 关键数据

---

## 5. Skill Loading：按需加载领域知识

### Skill 的本质
可复用的能力单元，包含五要素：触发条件、Prompt 模板、工具集合、输出约束、上下文策略

### 与 MCP 的区别
- MCP 提供工具（**能做什么**）
- Skill 提供知识和方法论（**怎么做**）

### 渐进式披露
- L0 索引层：只加载名称+一句话描述
- L1 摘要层：意图命中时加载步骤概要
- L2 完整层：确认执行时加载全部内容

---

## 6. Context Compact：三层压缩换无限会话

### 核心问题
读1000行文件约4000 token，读30个文件+20条命令可突破100k token。

### 三层压缩架构

#### Layer 1: Microcompact — 无 LLM 的静默清理
- 每次 LLM 调用前执行
- 将旧的 tool_result 替换为占位符
- 保留最近 3-5 个结果，早期替换为 `[Previous: used xxx]`
- **零延迟，不调用 LLM**

#### Layer 2: Full Compact — Fork Sonnet 生成结构化摘要
- Fork 一个 Sonnet 子进程生成摘要
- 输出包含 9 个结构化部分：
  1. Primary Request and Intent
  2. Key Technical Concepts
  3. Files and Code Sections
  4. Errors and Fixes
  5. Problem Solving
  6. All User Messages
  7. Pending Tasks
  8. Current Work
  9. Optional Next Step

#### Layer 3: Auto Compact — 阈值触发 + 熔断器
- 阈值 = context_window - max_output_tokens - 13,000
- 连续失败 3 次后停止重试
- 先尝试轻量 Session Memory，失败才回退 Full Compact

### 辅助机制：Session Memory
- 维护 markdown 格式笔记文件
- 10 个 section，全文上限 12000 token
- 双重门控：10K token 首次触发，后续需 5K token 增长 + 3 次工具调用

### 设计哲学
> "智能系统需要有选择地遗忘"
- **Microcompact**（持续遗忘）：每轮清理工具输出细节
- **Full Compact**（主动遗忘）：LLM 判断什么值得记住
- **Auto Compact**（防御性遗忘）：熔断器确保不崩溃

---

## 7. Task System：持久化任务图

将任务拆解为 DAG（有向无环图），支持：
- 任务依赖关系
- 断点恢复
- 进度追踪

---

## 8. Background Tasks：非阻塞工具执行

工具执行可以在后台进行，Agent 不被阻塞，继续处理其他任务。

---

## 9-11. Agent Teams：多 Agent 协作

### 从 Subagent 到 Teams 的进化

| 特性 | Subagent | Agent Teams |
|------|----------|-------------|
| 身份 | 一次性 | 持久（确定性 ID） |
| 通信 | 无（只返回结果） | 双向消息（mailbox + pending queue） |
| 并发 | 否 | 是 |
| 跨对话 | 否 | 是（TeamFile 持久化） |
| 关机 | 自动 | 协议驱动 |

### 核心组件
- **TeamCreate**：创建团队，确定 lead_agent_id
- **SendMessage**：三条路由路径（同进程/广播/跨session）
- **InProcessTeammateTask**：Teammate 是同一进程内的 Task

### Agent 生命周期状态机
```
WORKING → IDLE → 收到消息 → WORKING（auto-resume）
IDLE → SHUTDOWN_PENDING → 终止/继续
```

### 关键设计洞察
1. **消息队列 vs 直接调用**：正在执行的 teammate 收到消息不被打断
2. **两级 AbortController**：一个杀当前 turn，一个杀整个 teammate
3. **Leader 不是 Teammate**：不参与收件箱轮询，通过回调被动接收
4. **50 条消息 UI 上限**：防止内存爆炸（事故驱动设计）

### 设计哲学
> "在能力和控制之间取得平衡。多 Agent 系统很强大，但如果人类无法理解和干预，强大就变成了危险。"

---

## 12. Worktree 隔离：多 Agent 并行不踩踏

每个 Agent 在独立的 git worktree 中工作，避免文件冲突。

---

## 核心架构总结

Claude Code 的架构可以看作一个不断叠加防御层的过程：

```
30行 while 循环
  + Tool Use（外部能力）
  + TodoWrite（任务锚点）
  + Subagent（上下文隔离）
  + Skill（领域知识）
  + Context Compact（三层压缩）
  + Task System（持久化任务图）
  + Background Tasks（非阻塞执行）
  + Agent Teams（多Agent协作）
  + Worktree 隔离（并行安全）
```

每一层都是对基础循环的增强，解决特定的工程问题。
