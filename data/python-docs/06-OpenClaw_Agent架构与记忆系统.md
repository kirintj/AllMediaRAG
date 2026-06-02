# OpenClaw Agent 架构与记忆系统

> 来源：https://onefly.top/zero2Agent/learn-openclaw/
> 从 60 行核心框架推导到完整 Agent 系统

---

## 一、EventStream 驱动的 Agent Loop

### 双层循环结构
```
外层循环：等待用户消息 / 多轮对话
  └─ 内层循环：调用 LLM
       ├─ 有 tool_calls → 并行执行工具 → 结果追加 → 继续
       └─ 无 tool_calls → 结束
```

### EventStream 事件类型
| 事件 | 用途 |
|------|------|
| `agent_start/end` | Agent 生命周期 |
| `turn_start/end` | 一轮对话 |
| `message_start/update/end` | 模型生成（流式增量） |
| `tool_execution_start/update/end` | 工具执行 |

### 三大设计优势
1. **UI 解耦** — TUI、Web UI 消费同一 EventStream
2. **可观测性** — 每个事件是结构化数据
3. **可恢复性** — 事件序列即 transcript

### 并行工具执行
模型一次返回多个 tool_calls 时用 `Promise.all` 并行执行，延迟从 O(n) 降到 O(1)。

### 四个 Hook 介入点
| Hook | 功能 |
|------|------|
| `beforeToolCall` | 安全过滤、权限控制 |
| `afterToolCall` | 结果截断 |
| `transformContext` | 上下文压缩 |
| `convertToLlm` | 适配不同 Provider |

---

## 二、OpenClaw 五阶段执行模型

| 阶段 | 功能 |
|------|------|
| Stage 1: RPC Validation | 验证请求格式、权限、速率限制 |
| Stage 2: Skill Loading | 动态加载匹配的 Skill |
| Stage 3: Pi-Agent Runtime | 核心 Agent Loop |
| Stage 4: Event Bridging | 桥接到 Slack/飞书/Web |
| Stage 5: Persistence | JSONL 持久化 + MEMORY.md 更新 |

### 并发控制
Per-Session 串行化（文件级写锁），避免消息顺序混乱和上下文竞态。

### 多层超时
| 类型 | 时间 | 说明 |
|------|------|------|
| waitForInput | 30秒 | 等待用户输入 |
| maxRuntime | 48小时 | 最大运行时间 |
| idleWatchdog | 5分钟 | 无活动自动暂停 |
| toolExecution | 2分钟 | 单工具执行上限 |

---

## 三、三层记忆架构

### 第一层：MEMORY.md — 文件级持久化
选择 Markdown 文件的四个理由：
1. 人类可读可编辑
2. Git 友好（版本控制、diff、回滚）
3. 零依赖
4. LLM 原生格式

每条记忆是独立 `.md` 文件，MEMORY.md 充当索引。

### 第二层：Context Engine — 可插拔上下文管理

**五个核心方法**：bootstrap → ingest → **assemble** → compact → maintain

**assemble() 优先级**：
| 优先级 | 内容 |
|--------|------|
| 1（最高） | 系统指令 |
| 2 | MEMORY.md 索引 |
| 3 | 压缩摘要 |
| 4（最低） | 近期对话（从新到旧填充） |

> 预算不够时从低优先级开始裁剪。

### 第三层：Session 管理
解决：多用户隔离、断点续传、审计追踪

---

## 四、Dreaming 系统 — 记忆自动整理

三阶段合成：
| 阶段 | 工作 |
|------|------|
| **Light Sleep** | 扫描当日对话，提取候选记忆 |
| **Deep Sleep** | 合并相似主题、消除矛盾 |
| **REM** | 跨主题关联、生成新 Compiled Truth |

**记忆评分公式**：
```
Score = relevance(0.30) + frequency(0.24) + query_diversity(0.15)
      + recency(0.15) + consolidation(0.10) + conceptual_richness(0.06)
```

**关键约束**：只有 grounded snippets（有据可查）才有资格被提升，防止幻觉记忆。

> "记忆不是只写不删的日志，而是需要主动维护的知识库。"

---

## 五、Compaction — 标识符保留策略

### 三级保留模式
| 模式 | 保留内容 |
|------|----------|
| **strict**（推荐） | 文件路径、函数名、变量名、行号全部保留 |
| **relaxed** | 只保留文件路径和函数名 |
| **none** | 不做特殊保留 |

压缩前执行 auto-flush：关键信息写入 MEMORY.md，确保压缩不会导致知识丢失。

---

## 六、Claude Code vs OpenClaw 对比

| 维度 | Claude Code | OpenClaw |
|------|-------------|----------|
| 压缩策略 | LLM 摘要（无验证） | 标识符保留 + 质量检查点 |
| 记忆系统 | CLAUDE.md（单文件） | MEMORY.md + Daily Notes + DREAMS.md |
| Agent 隔离 | SubAgent（同进程） | 独立 workspace + 文件锁 |
| 工具安全 | 命令黑名单 | 分层调度 + 沙箱 + Ed25519 签名 |
| 缓存优化 | Prompt Caching（专有） | N/A → **Claude Code 胜** |
| 挫败检测 | 检测用户沮丧并调整 | ❌ → **Claude Code 胜** |

> Claude Code 是垂直集成产品，OpenClaw 是 provider-agnostic 的开放架构。

---

## 七、GBrain — 生产级外部记忆

### Compiled Truth + Timeline 模式
- **Compiled Truth**：Agent 直接使用的结论（可更新）
- **Timeline**：支撑结论的原始证据（不可变，只追加）

新信息到来时更新 Compiled Truth 而非简单追加。

### 设计原则
> "确定性操作优先于 LLM 判断"——实体抽取用正则，关系链接用模式匹配，仅在必须推理时才用 LLM。
