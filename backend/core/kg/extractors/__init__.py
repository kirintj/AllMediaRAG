"""GraphRAG 提取器"""
from .general_extractor import GeneralExtractor
from .light_extractor import LightExtractor
from .ner_extractor import NERExtractor

__all__ = ["GeneralExtractor", "LightExtractor", "NERExtractor"]
