# Agent 训练实战：从 SFT 到部署

> 来源：https://onefly.top/zero2Agent/learn-agent-training/
> 6 篇文章，Agent 场景下的训练技术全流程

---

## 1. Agent SFT 关键细节：从轨迹数据到 Loss Mask

### Agent SFT vs 对话 SFT

| 维度 | 对话 SFT | Agent SFT |
|------|----------|-----------|
| 训练目标 | 生成一个好回复 | 执行一整条正确的轨迹 |
| 数据粒度 | 单轮问答 | 多轮推理 + 工具调用 + 最终回复 |
| Token 类型 | 用户输入 + 模型回复 | System/User/Think/Tool Call/Tool Return/Response |
| Loss 计算 | 对模型回复算 loss | 需精细控制哪些 token 算 loss |

### 轨迹数据构造

**两条路径**：
- 人工标注：质量高但成本极高
- **强模型生成 + 人工筛选**：主流做法

**两个注意点**：
1. **必须包含失败轨迹**——只用成功轨迹训练出的 Agent 遇到失败会死循环
2. 轨迹长度要适中——太短学不到复杂流程，太长引入噪声

### Loss Mask：核心训练技巧

| 轨迹部分 | 计算 Loss? | 原因 |
|----------|-----------|------|
| System Prompt | ❌ | 模型不需要学生成这个 |
| User 消息 | ❌ | 同上 |
| Think 部分 | 看情况 | 质量高就留，质量差就 mask |
| **Tool Call** | **✅** | 核心学习目标 |
| Tool 返回结果 | ❌ | 环境返回的，不是模型生成的 |
| **最终回复** | **✅** | 学习根据工具结果总结输出 |

### 训练数据配比

| 数据类型 | 比例 | 说明 |
|---------|------|------|
| Agent 轨迹数据 | 40-50% | 核心但不能占太多 |
| Tool Calling 单轮 | 15-20% | function calling 基本功 |
| 通用指令跟随 | 15-20% | 保持正常对话能力 |
| 长文本理解 | 5-10% | Agent 天然上下文很长 |
| 安全/拒绝 | 5-10% | Agent 能真执行操作，安全更重要 |

> 安全数据比例高于对话模型：Agent 能实际执行操作（删文件、发请求、改数据库）

### SFT 与 RL 的配合

**技巧 1**：SFT 不要把完成率刷到 95%+，留到 70-80% 给 RL 留探索空间

**技巧 2**：SFT checkpoint 作为 RL 的 reference model（KL 约束），防止 RL 偏太远导致格式退化

---

## 2. GRPO vs PPO：Agent 强化学习算法深度对比

### 核心分歧：如何估计"平均水平"（基线）

| 维度 | PPO | GRPO |
|------|-----|------|
| Critic 网络 | 需要 | **不需要** |
| 显存占用 | 高（双网络） | 中（Policy + Reference） |
| 每 prompt rollout | 1 条 | N 条（通常 8） |
| 优势估计 | Value 网络 + GAE | 组内 Reward 归一化 |
| 信用分配 | step-level | trajectory-level |
| 代表工作 | InstructGPT, ChatGPT | DeepSeek-R1, Kimi-K1.5 |

### PPO 的三大问题（Agent 场景）
1. Critic 显存开销巨大（7B 模型 ~84GB+）
2. Critic 难训练（变长文本、稀疏 Reward、方差大）
3. Clip 机制过于保守

### GRPO 的关键设计
- **N=8 是大多数场景的甜点**
- temperature=0.7–1.0 保证轨迹多样性
- std 加下界（1e-4）防止除零

### 选型指南

| 场景 | 选择 |
|------|------|
| Reward 可自动计算且区分度高 | GRPO |
| GPU 显存紧张 | GRPO |
| 需要 step-level 精细优化 | PPO |
| Rollout 成本极高 | PPO |
| **混合方案** | 先 GRPO 粗调 → 后 PPO 精调 |

### 实战踩坑
1. GRPO 的 N 条轨迹要真正独立采样（temperature 不能太低）
2. PPO 的 Critic 不能用太旧的 checkpoint
3. **KL 约束不能省**——无 KL 会导致格式退化、重复循环、能力崩塌
4. 监控 Reward 分布而非只看均值

---

## 3. 训练数据配比实战

> Agent 不只吃轨迹数据，需要混合配比防止能力退化

---

## 4. Agent 评测：怎么衡量训练效果

评测维度需要覆盖：
- 任务完成率
- 工具调用正确率
- 步骤效率（实际步数 vs 最优步数）
- 鲁棒性（异常恢复率）

---

## 5. 从 SFT 到部署全流程

```
数据构造 → SFT 训练 → RL 训练（GRPO/PPO）→ 评测 → 量化 → 部署
```

---

## 学习建议

> 这 6 篇文章覆盖了 Agent 训练的完整链路。面试中 GRPO vs PPO 的对比是高频考点，理解 Loss Mask 策略和数据配比是展示工程经验的关键。
