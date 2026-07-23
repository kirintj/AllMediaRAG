"""OCR providers -- 文字识别模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 OcrModel 注册表。

每个 provider 实现 ``extract_text(image_path: str) -> str`` 接口。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── PaddleOCR ────────────────────────────────────────────────────────────────

class PaddleOCRProvider:
    """百度 PaddleOCR 文字识别"""

    _FACTORY_NAME = "PaddleOCR"

    def __init__(self, **kwargs):
        self._lang = kwargs.get("lang", "ch")

    def extract_text(self, image_path: str) -> str:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang=self._lang, show_log=False)
        result = ocr.ocr(image_path, cls=True)
        lines = []
        for line_group in result:
            if line_group:
                for line in line_group:
                    lines.append(line[1][0])
        return "\n".join(lines)


# ── Tesseract ────────────────────────────────────────────────────────────────

class TesseractOCRProvider:
    """Tesseract OCR 文字识别 (via pytesseract)"""

    _FACTORY_NAME = "Tesseract"

    def __init__(self, **kwargs):
        self._lang = kwargs.get("lang", "chi_sim+eng")
        self._tesseract_cmd = kwargs.get("tesseract_cmd", None)

    def extract_text(self, image_path: str) -> str:
        from PIL import Image
        import pytesseract

        if self._tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=self._lang)
        return text.strip()


# ── VLM (Vision LLM as OCR) ─────────────────────────────────────────────────

class VLMOCRProvider:
    """使用视觉大模型进行 OCR (OpenAI-compatible API)

    适用于 Qwen-VL、GPT-4o 等具备视觉能力的模型，
    通过向其发送图片并要求提取文字来实现 OCR。
    """

    _FACTORY_NAME = "VLM"

    def __init__(self, **kwargs):
        self._api_key = kwargs.get("api_key", "")
        self._model = kwargs.get("model_name", kwargs.get("model", "gpt-4o"))
        self._base_url = kwargs.get("base_url", None)
        self._prompt = kwargs.get(
            "prompt",
            "Please extract all text from this image. "
            "Return only the extracted text, preserving the original layout as much as possible.",
        )

    def extract_text(self, image_path: str) -> str:
        import base64
        from openai import OpenAI

        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # Determine image media type from extension
        ext = image_path.rsplit(".", 1)[-1].lower()
        media_type = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
            "bmp": "image/bmp",
        }.get(ext, "image/jpeg")

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": self._prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{image_base64}"},
                    },
                ],
            }],
        )
        return response.choices[0].message.content
