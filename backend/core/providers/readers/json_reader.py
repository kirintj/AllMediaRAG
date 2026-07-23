"""JSON 文件读取器"""
from __future__ import annotations
import json


class JsonReader:
    """读取 .json 文件，递归展平为可读文本"""

    def read(self, file_path: str) -> str:
        for encoding in ["utf-8", "utf-8-sig", "gbk", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    data = json.load(f)
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        else:
            return ""

        lines = self._flatten(data)
        return "\n".join(lines)

    def _flatten(self, obj, prefix: str = "") -> list[str]:
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    lines.extend(self._flatten(v, key))
                else:
                    lines.append(f"{key}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                key = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    lines.extend(self._flatten(item, key))
                else:
                    lines.append(f"{key}: {item}")
        else:
            lines.append(f"{prefix}: {obj}")
        return lines

    def supported_extensions(self) -> list[str]:
        return [".json"]
