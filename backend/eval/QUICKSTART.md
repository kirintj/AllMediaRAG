# 快速开始：生成简历量化数据

## 完整流程（约 15-20 分钟）

### Step 1: 安装依赖

```bash
cd backend
pip install ragas  # 如果还没安装 RAGAS
```

### Step 2: 运行 Baseline 评估

Baseline 代表"优化前"的状态。如果你的系统已经全部优化完，可以创建一个简化版引擎作为 baseline。

**方法 A: 如果你有 Git 历史**
```bash
# 切换到优化前的 commit
git checkout <优化前的commit>
python eval/run_eval.py --dataset extended --framework both --output eval/baseline_report.json
git checkout master
```

**方法 B: 如果没有历史，创建简化 baseline**
```bash
# 临时修改 config，禁用 Rerank 和查询改写
# 然后运行评估
python eval/run_eval.py --dataset extended --framework both --output eval/baseline_report.json
```

**方法 C: 跳过 baseline，直接用绝对值**
```bash
# 直接运行当前系统评估
python eval/run_eval.py --dataset extended --framework both --output eval/optimized_report.json
```

### Step 3: 运行优化后评估

```bash
python eval/run_eval.py --dataset extended --framework both --output eval/optimized_report.json
```

### Step 4: 生成 A/B 对比（如果有 baseline）

```bash
python eval/ab_comparison.py \
  --baseline eval/baseline_report.json \
  --optimized eval/optimized_report.json \
  --output eval/ab_comparison.md
```

### Step 5: 运行性能基准测试

```bash
python eval/performance_benchmark.py \
  --dataset eval/eval_dataset_extended.json \
  --output eval/performance_report.json
```

### Step 6: 生成简历数据

```bash
# 如果有 A/B 对比
python eval/generate_resume_data.py \
  --eval-report eval/ab_comparison.md \
  --perf-report eval/performance_report.json \
  --output eval/resume_metrics.md

# 如果只有优化后报告
python eval/generate_resume_data.py \
  --perf-report eval/performance_report.json \
  --output eval/resume_metrics.md
```

### Step 7: 查看结果

```bash
cat eval/resume_metrics.md
```

---

## 输出文件说明

| 文件 | 内容 |
|------|------|
| `eval/baseline_report.json` | Baseline 评估原始数据 |
| `eval/optimized_report.json` | 优化后评估原始数据 |
| `eval/ab_comparison.md` | A/B 对比报告 |
| `eval/performance_report.json` | 性能基准测试结果 |
| `eval/resume_metrics.md` | **简历可用数据汇总** |

---

## 常见问题

### Q: 运行评估要多久？
- 每个样本约 5-10 秒（检索 + 生成 + 评估）
- 20 题 × 2 个框架 ≈ 5-10 分钟
- 性能基准测试约 3-5 分钟

### Q: 评估失败怎么办？
1. 检查 API Key 是否配置正确
2. 检查 ChromaDB 是否有数据（运行过 indexing）
3. 查看错误日志，通常是 LLM 调用超时

### Q: 没有 baseline 怎么办？
用"绝对值"写法：
- MRR@10 达到 0.XX
- Faithfulness 达到 0.XX
- 响应时间 X.Xs

### Q: 数据不好看怎么办？
1. 优化切分策略（影响检索质量）
2. 优化 Rerank 模型（影响排序）
3. 增加评估数据集多样性
4. 多次运行取平均值

---

## 简历数据示例

运行完成后，`resume_metrics.md` 会包含类似这样的数据：

```
• 优化检索链路（多路召回 + Rerank + 二次检索），
  MRR@10 从 0.45 提升至 0.62（+37%），Hit Rate 从 68% 提升至 82%（+14%）

• 基于 RAGAS 框架搭建自动化评估，
  Faithfulness 达到 0.82，Answer Relevancy 达到 0.78

• 实现分层缓存 + 增量索引机制，
  平均响应时间 2.1s，缓存命中率 35%，支持 100+ 文档热更新
```

直接复制到简历即可！
