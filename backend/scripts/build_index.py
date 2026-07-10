"""Build chroma index for eval (lightweight: txt/md/pdf-text only)."""
import os
import sys
from pathlib import Path

# Disable heavy processors before import
os.environ["OCR_PROVIDER"] = "none"
os.environ["USE_VLM"] = "False"
os.environ["USE_VLM_EXTRACTOR"] = "False"
os.environ["MULTIMODAL_GENERATION"] = "False"

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "backend"))

# Force config reload with overrides via env
import importlib

# Patch config defaults (before RAGEngine instantiates bundles)
from core import config as _cfg_mod
_cfg_mod.config.OCR_PROVIDER = "none"
_cfg_mod.config.USE_VLM = False
_cfg_mod.config.USE_VLM_EXTRACTOR = False
_cfg_mod.config.MULTIMODAL_GENERATION = False
_cfg_mod.config.CHUNKING_STRATEGY = "semantic"

from core.rag_engine import RAGEngine


def main():
    print("Creating RAG engine...")
    e = RAGEngine(_cfg_mod.config)
    data_dir = project_root / "data" / "knowledge-base"
    print(f"Indexing: {data_dir} (exists={data_dir.exists()})")

    if not data_dir.exists():
        print("ERROR: data dir missing")
        sys.exit(1)

    stats = e.ingestion.sync_index(str(data_dir))
    print("stats:", stats)
    print("vector_count:", e.ingestion.get_index_stats())


if __name__ == "__main__":
    main()

