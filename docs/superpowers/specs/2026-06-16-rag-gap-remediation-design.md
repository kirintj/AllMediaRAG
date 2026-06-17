# RAG 全链路缺口补全设计方案

> 日期：2026-06-16
> 状态：Draft
> 范围：工厂模式补全、多模态 PDF 处理、测评体系完善

## 背景

基于全链路功能审计（覆盖离线索引、在线检索、测评、增量索引、分层缓存、工厂模式解耦共 29 项功能），发现以下缺口：

- **多模态处理短板**：PDF 内嵌图片/表格提取完全缺失，VLM 仅作用于独立图片文件
- **测评体系不完整**：缺 RAGAS 集成、Hit Rate 指标、自动化配置对比能力
- **工厂模式覆盖不均**：向量化和 Reranker 已解耦，但文档解析器、切分策略、查询改写仍硬编码

本方案按依赖顺序分三阶段递进补全。

---

## 阶段一：工厂模式补全

### 1.1 文档解析器工厂

**目标**：将 `DocumentProcessor` 中硬编码的解析逻辑提取为可插拔的 `FileReader` 实现。

**新增文件**：

```
backend/core/providers/readers/
├── __init__.py              # 导出所有 Reader
├── pdf_reader.py            # PDFReader(FileReader)
├── markdown_reader.py       # MarkdownReader(FileReader)
├── docx_reader.py           # DocxReader(FileReader)
├── html_reader.py           # HtmlReader(FileReader)
└── image_reader.py          # ImageReader(FileReader)
```

**接口定义**（基于已有的 `backend/core/providers/base.py` FileReader 基类）：

```python
class FileReader(ABC):
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名，如 ['.pdf']"""
        pass

    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """判断是否能处理该文件"""
        pass

    @abstractmethod
    def read(self, file_path: str, **kwargs) -> str:
        """提取文件文本内容，返回纯文本字符串"""
        pass
```

**改造 `DocumentProcessor`**：

- `__init__` 接收 `provider_factory` 参数
- `process_file()` 中通过 `factory.create_file_reader(ext)` 获取对应 Reader
- 原有 `_read_pdf` / `_read_markdown` / `_read_docx` / `_read_image` / `parse_html` 方法迁移到各 Reader 实现中
- `DocumentProcessor` 保留切分和元数据绑定逻辑不变

**注册机制**：在 `RAGEngine._init_with_factory()` 中注册所有 Reader：

```python
factory.register_file_reader(PDFReader(ocr_provider))
factory.register_file_reader(MarkdownReader())
factory.register_file_reader(DocxReader())
factory.register_file_reader(HtmlReader())
factory.register_file_reader(ImageReader(ocr_provider, vlm_provider))
```

### 1.2 切分策略抽象层

**目标**：将切分逻辑从 `DocumentProcessor` 中解耦，支持多种策略切换。

**新增文件**：

```
backend/core/chunking/
├── __init__.py
├── base.py                   # ChunkingStrategy(ABC)
├── semantic_strategy.py      # SemanticChunking — 当前语义切分逻辑
├── fixed_size_strategy.py    # FixedSizeChunking — 固定 token 数切分
└── recursive_strategy.py     # RecursiveChunking — 递归字符切分
```

**接口定义**：

```python
class ChunkData(TypedDict):
    content: str
    metadata: dict

class ChunkingStrategy(ABC):
    @abstractmethod
    def split(self, text: str, metadata: dict) -> list[ChunkData]:
        """将文本切分为 chunk 列表，每个 chunk 包含内容和元数据"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称，用于配置和日志"""
        pass
```

**策略实现**：

| 策略 | 类名 | 切分逻辑 |
|------|------|----------|
| semantic | SemanticChunking | 语义相似度切分（现有逻辑提取） |
| fixed_size | FixedSizeChunking | 按 token 数切分，支持 overlap |
| recursive | RecursiveChunking | 按段落→句子→字符递归切分 |

**配置**：在 `config.py` 新增：

```python
CHUNKING_STRATEGY: str = os.getenv("CHUNKING_STRATEGY", "semantic")
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))       # fixed_size/recursive 使用
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))   # overlap token 数
```

**工厂注册**：在 `ProviderFactory` 中新增 `register_chunking_strategy()` / `create_chunking_strategy()` 方法。

### 1.3 查询改写抽象层

**目标**：将查询改写策略从 `RAGEngine.__init__` 直接实例化改为可插拔注册。

**新增文件**：

```
backend/core/query_understanding/rewriters/
├── __init__.py
├── base.py                    # QueryRewriter(ABC)
├── hyde_rewriter.py           # HyDERewriter — 从 hyde_generator.py 提取
└── multi_query_rewriter.py    # MultiQueryRewriter — 从 multi_query.py 提取
```

**接口定义**：

```python
class QueryRewriter(ABC):
    @abstractmethod
    async def rewrite(self, query: str, context: dict = None) -> list[str]:
        """返回改写后的查询列表（不含原始查询）"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """改写器名称"""
        pass
```

**改造**：`RAGEngine` 通过配置列表选择启用哪些 rewriter，`QueryRouter` 决定每个查询实际调用哪些。原有 `hyde_generator.py` 和 `multi_query.py` 保留向后兼容的包装。

### 1.4 小问题修复

| 问题 | 修复方式 |
|------|----------|
| `CITATION_VERIFY_ENABLED` 未接线 | 在 `rag_engine.py` 和 `chat.py` 中添加 if 检查 |
| `RETRIEVAL_REFETCH_ENABLED` 未接线 | 在 `rag_engine.py` 二次检索逻辑前添加 if 检查 |
| `full_retrieve()` 重复 `router.route()` 调用 | 移除第二次调用（约 line 671） |
| `QueryClassifier` 忽略 `llm_client` 参数 | 移除该参数或添加 LLM 分类器实现 |

---

## 阶段二：多模态 PDF 处理

### 2.1 EnhancedPDFReader

**目标**：替代原有 `PDFReader`，支持文本、图片、表格三种内容类型的提取。

**新增文件**：

```
backend/core/providers/readers/enhanced_pdf_reader.py   # 替代 pdf_reader.py
```

**新增依赖**：

```
PyMuPDF>=1.24.0       # fitz — PDF 内嵌图片提取 + 高质量文本提取
pdfplumber>=0.11.0     # 表格提取
```

**处理流程**：

```
PDF 文件输入
  │
  ├─ 逐页处理 ─────────────────────────────────────────────┐
  │   │                                                     │
  │   ├─ 文本提取（PyMuPDF）                                │
  │   │   └─ 支持多栏布局，替代 PyPDF2                      │
  │   │                                                     │
  │   ├─ 内嵌图片提取（PyMuPDF extract_images）             │
  │   │   ├─ 过滤 < 100x100 装饰性图片                     │
  │   │   ├─ 保存到临时目录                                 │
  │   │   ├─ 调用 OCRProvider.extract_text()               │
  │   │   ├─ 调用 VLMProvider.describe_image()             │
  │   │   └─ 注入 [图片OCR] + [图片描述] 标签到文本流      │
  │   │                                                     │
  │   ├─ 表格提取（pdfplumber）                             │
  │   │   ├─ detect_tables() 检测表格区域                   │
  │   │   ├─ extract_table() 提取为二维列表                 │
  │   │   ├─ 转换为 Markdown table 格式                    │
  │   │   └─ 注入 [表格] 标签到文本流                       │
  │   │                                                     │
  │   └─ 扫描页面检测（< 50 字符/页）                      │
  │       └─ 整页转图片 → OCR                              │
  │                                                        │
  └─ 合并所有页面内容 → 返回完整文本                       │
```

**类设计**：

```python
class EnhancedPDFReader(FileReader):
    """增强型 PDF 解析器，支持文本、图片、表格多模态提取"""

    def __init__(self, ocr_provider: OCRProvider = None,
                 vlm_provider: VLMProvider = None):
        self.ocr = ocr_provider
        self.vlm = vlm_provider
        self._temp_dir = None  # 临时图片目录

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def read(self, file_path: str, **kwargs) -> str:
        """提取 PDF 全部内容（文本 + 图片描述 + 表格）"""
        ...

    def _extract_page_text(self, page) -> str:
        """PyMuPDF 文本提取"""
        ...

    def _extract_page_images(self, page, page_num: int) -> list[str]:
        """提取页面内嵌图片，返回图片描述列表"""
        ...

    def _extract_page_tables(self, page, page_num: int) -> list[str]:
        """提取页面表格，返回 Markdown 格式表格列表"""
        ...

    def _process_scanned_page(self, page, page_num: int) -> str:
        """处理扫描页面（整页 OCR）"""
        ...
```

**临时文件管理**：
- 使用 `tempfile.TemporaryDirectory()` 作为图片临时存储
- 所有图片处理完毕后自动清理
- 通过 `__del__` 和 context manager 双重保障

### 2.2 与工厂模式的集成

`EnhancedPDFReader` 作为 `PDFReader` 的增强版注册到工厂：

```python
# 在 RAGEngine._init_with_factory() 中
pdf_reader = EnhancedPDFReader(
    ocr_provider=self.ocr_provider,
    vlm_provider=self.vlm_provider
)
factory.register_file_reader(pdf_reader)
```

阶段一建立的 FileReader 接口天然支持阶段二的扩展，无需修改 `DocumentProcessor`。

---

## 阶段三：测评体系完善

### 3.1 RAGAS 集成

**目标**：接入 RAGAS 标准评估框架，与现有自研评估器并存互补。

**新增文件**：

```
backend/eval/ragas_evaluator.py    # RAGAS 标准评估器
```

**新增依赖**：

```
ragas>=0.2.0
```

**设计**：

```python
class RAGASEvaluator:
    """基于 RAGAS 框架的标准评估器"""

    METRICS = {
        "faithfulness": Faithfulness,
        "answer_relevancy": AnswerRelevancy,
        "context_precision": ContextPrecision,
        "context_recall": ContextRecall,
    }

    def evaluate(self, dataset: list[dict]) -> dict:
        """
        输入格式：[{question, contexts, answer, ground_truth}]
        输出格式：与现有 evaluator 的 report.json 结构对齐
        """
        ...

    def evaluate_single(self, sample: dict) -> dict:
        """单条样本评估"""
        ...
```

**集成点**：改造 `backend/eval/run_eval.py`，新增 `--framework` 参数：

```bash
# 使用自研评估器（默认，向后兼容）
python -m backend.eval.run_eval --dataset eval.json

# 使用 RAGAS 评估器
python -m backend.eval.run_eval --dataset eval.json --framework ragas
```

### 3.2 Hit Rate 指标

**新增文件**：

```
backend/eval/metrics.py    # 自定义评估指标集合
```

**实现**：

```python
def hit_rate(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """至少命中一个相关文档返回 1.0，否则 0.0"""
    return 1.0 if any(src in expected_sources for src in retrieved_sources) else 0.0

def recall_at_k(retrieved_sources: list[str], expected_sources: set[str], k: int) -> float:
    """前 K 个结果中命中的相关文档比例"""
    retrieved_top_k = retrieved_sources[:k]
    hits = sum(1 for src in retrieved_top_k if src in expected_sources)
    return hits / len(expected_sources) if expected_sources else 0.0
```

**集成**：在 `evaluator.py` 的 `_aggregate()` 方法中新增 hit_rate 聚合，与 MRR、Recall@K 并列输出到报告。

### 3.3 自动化配置对比框架

**新增文件**：

```
backend/eval/config_comparator.py    # 配置对比评估器
```

**设计**：

```python
class ConfigComparator:
    """自动化多配置对比评估"""

    def compare(self, base_config: dict, candidates: list[dict],
                dataset_path: str) -> ComparisonReport:
        """
        1. 用 base_config 运行评估作为基准
        2. 遍历每个候选配置运行评估
        3. 汇总对比报告
        """
        ...

@dataclass
class ComparisonReport:
    """对比报告"""
    baseline: dict          # 基准配置的指标
    candidates: list[dict]  # 各候选配置的指标
    best_config: dict       # 最优配置
    summary_table: str      # Markdown 格式对比表格
```

**可对比维度**：

| 维度 | 配置键 | 可选值 |
|------|--------|--------|
| 切分策略 | CHUNKING_STRATEGY | semantic, fixed_size, recursive |
| 向量召回数 | TOP_K | 3, 5, 10, 20 |
| BM25 召回数 | BM25_TOP_K | 3, 5, 10, 20 |
| RRF 融合权重 | RRF_WEIGHT_VECTOR | 0.3, 0.5, 0.7 |
| Rerank 策略 | RERANK_STRATEGY | cohere, bge, hybrid |
| Rerank 候选数 | RERANK_TOP_K | 3, 5, 10 |

**CLI 接口**：

```bash
python -m backend.eval.config_comparator \
  --dataset eval_dataset.json \
  --compare chunking_strategy:semantic,fixed_size \
  --compare rrf_weight_vector:0.5,0.7 \
  --output comparison_report.md
```

---

## 项目结构变更总览

```
backend/
├── core/
│   ├── chunking/                              # 新增：切分策略
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── semantic_strategy.py
│   │   ├── fixed_size_strategy.py
│   │   └── recursive_strategy.py
│   ├── providers/
│   │   ├── readers/                           # 新增：文档解析器
│   │   │   ├── __init__.py
│   │   │   ├── pdf_reader.py
│   │   │   ├── enhanced_pdf_reader.py         # 阶段二新增
│   │   │   ├── markdown_reader.py
│   │   │   ├── docx_reader.py
│   │   │   ├── html_reader.py
│   │   │   └── image_reader.py
│   │   ├── factory.py                         # 改造：注册 Reader 和 ChunkingStrategy
│   │   └── base.py                            # 改造：补充 ChunkingStrategy 基类
│   ├── query_understanding/
│   │   ├── rewriters/                         # 新增：查询改写策略
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── hyde_rewriter.py
│   │   │   └── multi_query_rewriter.py
│   │   ├── classifier.py                      # 改造：修复 llm_client 参数
│   │   ├── router.py                          # 保持不变
│   │   ├── hyde_generator.py                  # 保留：向后兼容包装
│   │   └── multi_query.py                     # 保留：向后兼容包装
│   ├── document_processor.py                  # 改造：走工厂获取 Reader 和 ChunkingStrategy
│   ├── rag_engine.py                          # 改造：接入新架构 + 修复 config flag
│   └── config.py                              # 改造：新增配置项
├── eval/
│   ├── evaluator.py                           # 改造：新增 hit_rate 聚合
│   ├── ragas_evaluator.py                     # 新增：RAGAS 评估器
│   ├── metrics.py                             # 新增：自定义指标
│   ├── config_comparator.py                   # 新增：配置对比框架
│   └── run_eval.py                            # 改造：--framework 参数
├── api/
│   └── chat.py                                # 改造：接入 CITATION_VERIFY_ENABLED
└── requirements.txt                           # 改造：新增 PyMuPDF, pdfplumber, ragas
```

## 依赖变更

```diff
# requirements.txt 新增
+ PyMuPDF>=1.24.0
+ pdfplumber>=0.11.0
+ ragas>=0.2.0
```

## 新增配置项

```diff
# .env / config.py 新增
+ CHUNKING_STRATEGY=semantic          # semantic | fixed_size | recursive
+ CHUNK_SIZE=512                      # fixed_size/recursive 的 chunk 大小
+ CHUNK_OVERLAP=50                    # chunk 重叠 token 数
+ EVAL_FRAMEWORK=custom               # custom | ragas
```

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| PyMuPDF 安装可能需要系统依赖 | PyMuPDF 纯 pip 安装，无系统依赖，优于 poppler |
| pdfplumber 表格检测误判 | 保留回退逻辑：检测失败时按普通文本提取 |
| RAGAS 依赖冲突 | 独立评估脚本，不侵入主服务启动流程 |
| 现有 PDF 解析行为变更 | EnhancedPDFReader 作为新实现注册，可通过配置回退到原 PDFReader |
| 切分策略切换后向量库数据不一致 | 切换策略后需 rebuild 索引（sync_index --force） |

## 实施顺序

1. **阶段一** → 工厂模式补全（基础设施，约 2-3 天）
2. **阶段二** → 多模态 PDF 处理（核心能力，约 2 天）
3. **阶段三** → 测评体系完善（验证层，约 1-2 天）

每个阶段完成后可独立验证，不影响现有功能。
