# 切分策略对比报告

| 策略 | MRR | Recall@K | NDCG@K | MAP | Faithfulness | 平均块大小 | 耗时(s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_size | 0.9600 | 1.0000 | 1.5365 | 1.9000 | 4.95 | 122 | 633.9 |
| recursive | 0.9600 | 1.0000 | 1.4992 | 1.8430 | 4.95 | 132 | 664.7 |
| semantic | 0.9500 | 0.9500 | 1.5176 | 1.8283 | 5.0 | 162 | 603.4 |
| parent_child | 0.9500 | 0.9500 | 1.5201 | 1.8417 | 4.95 | 167 | 638.7 |

## 参数配置

### fixed_size
- `CHUNKING_STRATEGY`: fixed_size
- `CHUNK_SIZE`: 512
- `CHUNK_OVERLAP`: 50
- 平均召回块数: 5.4
- 平均块大小: 122 字符

### recursive
- `CHUNKING_STRATEGY`: recursive
- `CHUNK_SIZE`: 512
- `CHUNK_OVERLAP`: 50
- 平均召回块数: 5.4
- 平均块大小: 132 字符

### semantic
- `CHUNKING_STRATEGY`: semantic
- `SEMANTIC_CHUNK_PERCENTILE`: 25
- 平均召回块数: 5.4
- 平均块大小: 162 字符

### parent_child
- `CHUNKING_STRATEGY`: parent_child
- `PC_CHILD_SENTENCES`: 3
- `PC_PARENT_GROUPS`: 4
- 平均召回块数: 5.2
- 平均块大小: 167 字符
