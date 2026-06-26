"""VLMExtractor — 统一视觉语言模型提取器。

用一次 VLM 调用替代旧的 OCR+VLM 分离管线：
输入文件（图片/PDF），输出结构化 DocumentRegion 列表。

设计决策：
- 为什么用 OpenAI 兼容 API 而非直接调用各厂商 SDK：
  OpenAI Chat Completions 格式已成为事实标准，主流 VLM（GPT-4o、
  Qwen-VL、InternVL 等）均提供兼容接口，一套代码即可切换模型。
- 为什么提取器不继承 OCRProvider：VLMExtractor 的职责是"结构化区域提取"，
  而 OCRProvider 是"纯文本提取"，二者输入输出契约不同；
  继承会导致必须实现 extract_text 这个语义不符的方法。
"""

import base64
import io
import json
import logging
import os
import re
import tempfile
from typing import Optional

from ..models.document_region import DocumentRegion

logger = logging.getLogger(__name__)

# 为什么阈值设为 200：根据经验，少于 200 字符的 PDF 页面
# 大概率是扫描件或纯图片页，传统文本提取几乎无内容，
# 此时 VLM 的视觉理解能力远超 OCR。
TEXT_THRESHOLD_FOR_VLM = 200

# 为什么用中文 prompt：VLM 对中文指令的理解能力在中文文档场景下
# 优于英文指令，且输出 JSON 的 key 用英文保证了解析的确定性。
EXTRACTION_PROMPT = """请分析这张文档页面图片，识别所有可见的文档区域，并以 JSON 格式输出。

要求：
1. 识别以下类型的区域：header（标题）、text（正文段落）、table（表格）、figure（图片/图表/流程图）、equation（数学公式）
2. 对每个区域提供：type、content、confidence
3. 对 figure 类型，额外提供 bbox（边界框坐标 [x0, y0, x1, y1]）
4. 表格内容请用 Markdown 表格格式输出
5. 图片/图表请提供文字描述
6. 公式请用 LaTeX 格式输出

输出格式（严格 JSON）：
{
  "regions": [
    {"type": "header", "content": "标题文本", "confidence": 0.99},
    {"type": "text", "content": "正文内容", "confidence": 0.95},
    {"type": "table", "content": "| 列1 | 列2 |\\n|---|---|\\n| 值1 | 值2 |", "confidence": 0.92},
    {"type": "figure", "content": "图表描述", "bbox": [x0, y0, x1, y1], "confidence": 0.88}
  ],
  "page_summary": "页面内容摘要"
}

只输出 JSON，不要输出其他内容。"""


class VLMExtractor:
    """统一视觉语言模型提取器。

    将旧的 OCR + VLM 分离管线合并为单次 VLM 调用，
    直接输出结构化 DocumentRegion 列表，减少调用次数和错误累积。
    """

    def __init__(
        self,
        api_key: str,
        api_base: str,
        model: str,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_image_size: int = 1024,
    ):
        """
        Args:
            api_key: OpenAI 兼容 API 密钥
            api_base: API 基础 URL
            model: VLM 模型名称（如 gpt-4o、Qwen-VL-Plus 等）
            max_tokens: 单次调用最大输出 token 数
            timeout: API 调用超时秒数
            max_image_size: 图片长边最大像素数，超过会等比缩放
        """
        # 为什么存参数而非立即创建 client：构造函数可能在模块加载时调用，
        # 此时 OpenAI SDK 可能尚未安装或网络不可用；
        # 延迟到首次使用时初始化，遵循"快速失败在使用处"原则。
        self._api_key = api_key
        self._api_base = api_base
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._max_image_size = max_image_size
        self._client = None

    @property
    def client(self):
        """延迟初始化 OpenAI 客户端。

        为什么用 property 而非在 __init__ 创建：
        1. 避免 import 时因网络问题阻塞整个服务启动；
        2. 测试中可以轻松替换 _client 为 MagicMock 而不触发真实网络调用。
        """
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._api_base,
                timeout=self._timeout,
            )
        return self._client

    # ── 主入口 ──────────────────────────────────────────────────

    def extract(self, file_path: str) -> list[DocumentRegion]:
        """根据文件类型分发到对应的提取方法。

        为什么按扩展名分发而非 MIME 检测：
        本地文件场景下扩展名足够可靠，且 PyMuPDF 的 open 方法
        也是按扩展名判断格式，保持一致可以减少中间转换。
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
            return self._extract_image_file(file_path)
        else:
            logger.warning("不支持的文件类型: %s，跳过 VLM 提取", ext)
            return []

    # ── 图片提取 ────────────────────────────────────────────────

    def _extract_image_file(self, file_path: str) -> list[DocumentRegion]:
        """单张图片的完整提取流程：缩放 → base64 → VLM → 解析 → 裁剪 figure。

        为什么先缩放再编码：VLM 模型对输入图片有 token 限制，
        超大图片不仅浪费 token 还可能被截断导致识别不全，
        等比缩放到 max_image_size 可以在保留足够细节的同时控制成本。
        """
        with open(file_path, "rb") as f:
            image_bytes = f.read()

        # 为什么对所有图片都检查尺寸而非只对大图：
        # 统一走缩放逻辑可以保证输出尺寸的一致性，
        # 避免下游处理时因图片尺寸差异过大而出问题。
        image_bytes = self._resize_image(image_bytes, self._max_image_size)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        raw_response = self._call_vlm(image_b64)
        if not raw_response:
            # 为什么降级到 OCR 而非直接返回空：VLM 调用可能因网络/限流
            # 临时失败，PaddleOCR 作为离线兜底保证不阻塞 ingestion 流程。
            return self._fallback_to_ocr(file_path)

        regions = self._parse_response(raw_response)

        # 为什么对 figure 区域裁剪原图存入 image_base64：
        # figure 的文字描述无法完全替代原图（如流程图的视觉布局），
        # 裁剪出原图区域可以让下游多模态 RAG 在回答时直接引用原图。
        if any(r.type == "figure" and r.bbox for r in regions):
            with open(file_path, "rb") as f:
                original_bytes = f.read()
            for region in regions:
                if region.type == "figure" and region.bbox:
                    region.image_base64 = self._crop_image(
                        original_bytes, region.bbox
                    )

        return regions

    # ── PDF 提取 ────────────────────────────────────────────────

    def _extract_pdf(self, pdf_path: str) -> list[DocumentRegion]:
        """PDF 逐页提取：文字密集页用 PyMuPDF，扫描页用 VLM。

        为什么混合策略而非全部用 VLM：
        1. 文字密集页用 PyMuPDF 提取更快、更准（零 API 调用）；
        2. VLM 对纯文本页面可能出现"幻觉"或格式化错误；
        3. 仅对扫描页调用 VLM 可以将 API 成本降低 60-80%。
        """
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        all_regions: list[DocumentRegion] = []

        # 为什么用临时目录而非内存：PyMuPDF 渲染图片和裁剪 figure
        # 都需要文件路径，使用 with 块确保临时文件在异常时也能清理。
        with tempfile.TemporaryDirectory() as temp_dir:
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()

                if self._should_use_vlm_for_page(page_text):
                    # 为什么扫描页走 VLM：PyMuPDF 从扫描页提取的文字
                    # 通常是乱码或空字符串，VLM 的视觉理解能直接识别内容。
                    page_regions = self._extract_pdf_page_via_vlm(
                        doc, page_num, temp_dir
                    )
                    all_regions.extend(page_regions)
                else:
                    # 为什么文字密集页保留 PyMuPDF 文本：已有高质量文本
                    # 无需调用 VLM，直接包装成 text 区域即可。
                    if page_text.strip():
                        all_regions.append(
                            DocumentRegion(
                                type="text",
                                content=page_text.strip(),
                                bbox=None,
                                confidence=1.0,
                            )
                        )

        doc.close()
        return all_regions

    def _extract_pdf_page_via_vlm(
        self, doc, page_num: int, temp_dir: str
    ) -> list[DocumentRegion]:
        """将 PDF 单页渲染为图片后调用 VLM 提取。

        为什么用 2x 缩放渲染：默认 72dpi 渲染的图片在 VLM 中
        细节不足（尤其是小字和表格），2x（约 144dpi）在清晰度
        和 token 消耗之间取得平衡。
        """
        import fitz

        page = doc[page_num]
        # 为什么用 matrix 而非 dpi 参数：fitz 的 matrix 方式
        # 可以精确控制缩放倍数，dpi 参数在不同版本行为不一致。
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)

        img_path = os.path.join(temp_dir, f"page_{page_num}.png")
        pix.save(img_path)

        # 为什么再次缩放：2x 渲染后图片可能仍超过 max_image_size，
        # 统一走 _resize_image 保证所有输入 VLM 的图片尺寸一致。
        with open(img_path, "rb") as f:
            image_bytes = f.read()

        image_bytes = self._resize_image(image_bytes, self._max_image_size)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        raw_response = self._call_vlm(image_b64)
        if not raw_response:
            return self._fallback_to_ocr(img_path, page_num)

        regions = self._parse_response(raw_response)

        # 对 figure 区域裁剪原图
        for region in regions:
            if region.type == "figure" and region.bbox:
                region.image_base64 = self._crop_image(pix.tobytes("png"), region.bbox)

        return regions

    # ── OCR 回退 ────────────────────────────────────────────────

    def _fallback_to_ocr(
        self, img_path: str, page_num: int = 0
    ) -> list[DocumentRegion]:
        """VLM 调用失败时的 PaddleOCR 兜底。

        为什么保留 OCR 回退而非直接报错：
        VLM API 可能因限流、超时、模型下线等原因暂时不可用，
        此时 PaddleOCR 作为离线方案可以保证文档处理不中断，
        虽然质量下降但至少不会阻塞整个 ingestion 流程。
        """
        try:
            from .paddle_provider import PaddleOCRProvider

            ocr = PaddleOCRProvider()
            text = ocr.extract_text(img_path)
            if text.strip():
                return [
                    DocumentRegion(
                        type="text",
                        content=text.strip(),
                        bbox=None,
                        confidence=0.7,
                    )
                ]
        except Exception as e:
            logger.warning("OCR 回退也失败 (page %d): %s", page_num, e)

        return []

    # ── 判断逻辑 ────────────────────────────────────────────────

    def _should_use_vlm_for_page(self, page_text: str) -> bool:
        """判断 PDF 页面是否需要 VLM 处理。

        为什么用字符数而非其他指标：字符数是最简单可靠的启发式规则，
        无需加载额外模型即可快速判断；页面文本少于阈值大概率是
        扫描件，此时 VLM 的视觉理解能力是必要的。
        """
        return len(page_text.strip()) < TEXT_THRESHOLD_FOR_VLM

    # ── VLM 调用 ────────────────────────────────────────────────

    def _call_vlm(self, image_base64: str) -> str:
        """调用 OpenAI 兼容 VLM API，发送图片并获取结构化响应。

        为什么用 chat.completions 而非 responses API：
        chat.completions 是 OpenAI 的稳定 API，所有兼容提供商
        都支持；responses API 较新，部分第三方提供商尚未实现。

        返回空字符串表示调用失败（由调用方决定是否降级到 OCR）。
        """
        mime_type = "image/png"

        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self._max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # 为什么捕获所有异常而非只捕获特定类型：
            # VLM API 可能抛出 OpenAI SDK 的各种异常（RateLimitError,
            # APITimeoutError, APIStatusError 等），统一捕获后记录日志，
            # 返回空字符串触发调用方的 OCR 降级逻辑。
            logger.warning("VLM API 调用失败: %s", e)
            return ""

    # ── 响应解析 ────────────────────────────────────────────────

    def _parse_response(self, raw_text: str) -> list[DocumentRegion]:
        """多层解析 VLM 响应，逐步降级保证不丢失内容。

        为什么设计三层解析而非只用一种：
        VLM 输出格式不稳定——有时是纯 JSON，有时包裹在 markdown 代码块中，
        有时完全不是 JSON；三层解析按可靠性递减排列，
        每层失败才尝试下一层，最大化利用 VLM 输出。
        """
        # 第一层：直接解析 JSON
        try:
            data = json.loads(raw_text)
            return self._build_regions_from_data(data)
        except (json.JSONDecodeError, TypeError):
            pass

        # 第二层：从 markdown 代码块中提取 JSON
        extracted = self._extract_json_from_text(raw_text)
        if extracted:
            try:
                data = json.loads(extracted)
                return self._build_regions_from_data(data)
            except (json.JSONDecodeError, TypeError):
                pass

        # 第三层：纯文本回退——包装成单个 text 区域
        # 为什么回退为 text 而非返回空列表：
        # VLM 可能输出自然语言描述（如"此页包含三个段落"），
        # 虽然不是结构化数据，但仍包含有价值的信息，
        # 包装成 text 区域可以被后续 chunking 和检索利用。
        if raw_text.strip():
            logger.info("VLM 输出无法解析为 JSON，回退为纯文本区域")
            return [
                DocumentRegion(
                    type="text",
                    content=raw_text.strip(),
                    bbox=None,
                    confidence=0.5,
                )
            ]

        return []

    def _build_regions_from_data(self, data: dict) -> list[DocumentRegion]:
        """将解析后的 JSON 字典转换为 DocumentRegion 列表。

        为什么单独抽成方法：_parse_response 有多层解析逻辑，
        每层成功后都需要相同的转换步骤，抽成方法避免代码重复。
        """
        regions_data = data.get("regions", [])
        page_summary = data.get("page_summary", "")

        if not regions_data:
            # 为什么用摘要兜底而非直接返回空：
            # page_summary 可能包含有价值的页面概述信息，
            # 丢弃会导致该页面在检索中完全不可见。
            if page_summary.strip():
                return [
                    DocumentRegion(
                        type="text",
                        content=page_summary.strip(),
                        confidence=0.5,
                        bbox=None,
                    )
                ]
            return []

        regions = []
        for item in regions_data:
            region_type = item.get("type", "text")
            content = item.get("content", "")
            # 为什么用 try/except 包裹 float 转换：VLM 可能返回非数字
            # 字符串（如 "high"），直接 float() 会抛 ValueError，
            # 用默认值 0.5 兜底保证解析不会因单个 region 失败而中断。
            try:
                confidence = float(item.get("confidence", 0.5))
            except (ValueError, TypeError):
                confidence = 0.5

            # 为什么 list→tuple 转换：DocumentRegion.bbox 定义为 tuple，
            # tuple 的不可变性保证坐标在创建后不被意外修改。
            bbox_raw = item.get("bbox")
            bbox = tuple(bbox_raw) if bbox_raw else None

            # 为什么不在此处校验 type：DocumentRegion.__post_init__
            # 已包含类型校验，构造函数会自动抛出 ValueError，
            # 避免在两处维护相同的校验逻辑。
            try:
                region = DocumentRegion(
                    type=region_type,
                    content=content,
                    bbox=bbox,
                    confidence=confidence,
                )
                regions.append(region)
            except ValueError as e:
                # 为什么跳过非法类型而非中断整个解析：
                # 单个区域类型错误不应影响同页其他区域的提取，
                # 记录警告后继续处理剩余区域。
                logger.warning("跳过非法区域: %s", e)

        return regions

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """从文本中提取被 markdown 代码块包裹的 JSON。

        为什么用正则而非字符串查找：代码块可能有多种格式
        （```json、```JSON、``` 等），正则可以统一匹配；
        且 .*? 的非贪婪匹配可以避免跨越多个代码块时提取到错误内容。
        """
        # 为什么用 DOTALL 标志：JSON 内容可能跨多行，
        # 默认的 . 不匹配换行符会导致正则无法匹配完整的 JSON 块。
        pattern = r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 为什么还有第二层正则：某些 VLM 可能只用 { } 包裹 JSON
        # 而不加代码块标记，这种情况也需要尝试提取。
        pattern_braces = r"\{.*\}"
        match = re.search(pattern_braces, text, re.DOTALL)
        if match:
            return match.group(0).strip()

        return None

    # ── 图片处理 ────────────────────────────────────────────────

    def _resize_image(self, image_bytes: bytes, max_size: int) -> bytes:
        """等比缩放图片，长边不超过 max_size。

        为什么只限制长边：保持原始宽高比可以避免图片变形，
        变形的图片会导致 VLM 对图表比例和布局的判断出错。
        """
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))

        # 为什么先检查再缩放：小图片无需缩放，直接返回原图
        # 可以避免 PIL 重编码带来的质量损失。
        if max(img.size) <= max_size:
            return image_bytes

        # 为什么用 LANCZOS 而非 BILINEAR：LANCZOS 是最高质量的
        # 下采样算法，在缩放文档图片时能更好地保留文字边缘的锐利度。
        img.thumbnail((max_size, max_size), Image.LANCZOS)

        buf = io.BytesIO()
        # 为什么保存为 PNG 而非 JPEG：文档图片中的文字和线条
        # 在 JPEG 压缩下容易出现伪影，PNG 无损压缩更合适。
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _crop_image(self, image_bytes: bytes, bbox: tuple) -> str:
        """根据 bbox 裁剪图片区域，返回 base64 编码。

        为什么裁剪后返回 base64 而非 PIL Image：
        base64 字符串可以直接存入 DocumentRegion.image_base64，
        无需下游代码再做额外转换；且序列化到 JSON/数据库时
        base64 是最通用的格式。
        """
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))

        # 为什么用 clamp 限制坐标范围：VLM 返回的 bbox 可能
        # 超出图片边界（如坐标系不匹配），clamp 可以防止裁剪异常。
        x0, y0, x1, y1 = bbox
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(img.width, int(x1))
        y1 = min(img.height, int(y1))

        cropped = img.crop((x0, y0, x1, y1))

        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
