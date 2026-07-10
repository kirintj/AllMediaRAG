"""Lightweight in-memory/numpy vector store (no Chroma/HNSW).

Avoids the Windows memory allocation crash from Chroma's compactor
while keeping identical API surface.  Intended for evaluation runs
on machines with limited RAM.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from core.providers.base import VectorStoreProvider


class SimpleVectorStore(VectorStoreProvider):
    """Minimal vector store: JSON + numpy cosine similarity.

    Not optimized for scale; sufficient for evaluation datasets in the
    few-thousand chunk range.
    """

    def __init__(self, persist_dir: str | Path) -> None:
        self._path = Path(persist_dir) / "simple_vectors.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._docs: list[dict[str, Any]] = []  # {id, text, metadata, embedding}
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._docs = raw.get("docs", [])
            except Exception:
                self._docs = []
        self._rebuild_index()

    # ------------------------------------------------------------------
    # persistence helpers
    # ------------------------------------------------------------------
    def _persist(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump({"docs": self._docs}, f, ensure_ascii=False)
        except Exception:
            pass

    def _rebuild_index(self) -> None:
        if not self._docs:
            self._matrix = np.zeros((0, 0), dtype=np.float32)
            self._norms = np.zeros(0, dtype=np.float32)
            return
        vecs = np.array([d["embedding"] for d in self._docs], dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1e-12
        self._matrix = vecs / norms
        self._norms = norms[:, 0]

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not texts:
            return
        for text, emb, meta in zip(texts, embeddings, metadatas):
            self._docs.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "metadata": meta or {},
                "embedding": list(emb) if emb is not None else [],
            })
        self._rebuild_index()
        self._persist()

    def query(self, embedding: list[float], top_k: int) -> dict[str, list]:
        if self._matrix.shape[0] == 0 or embedding is None:
            return {"documents": [], "metadatas": [], "distances": []}
        q = np.asarray(embedding, dtype=np.float32)
        norm = np.linalg.norm(q) or 1e-12
        q = q / norm
        sims = self._matrix @ q  # cosine similarity
        top_k = max(1, min(top_k, len(sims)))
        idx = np.argpartition(-sims, top_k - 1)[:top_k]
        idx = idx[np.argsort(-sims[idx])]
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        distances: list[float] = []
        for i in idx:
            documents.append(self._docs[i]["text"])
            metadatas.append(self._docs[i]["metadata"])
            distances.append(float(1.0 - sims[i]))
        return {"documents": documents, "metadatas": metadatas, "distances": distances}

    def delete_by_source(self, source: str) -> None:
        self._docs = [d for d in self._docs if d.get("metadata", {}).get("source") != source]
        self._rebuild_index()
        self._persist()

    def get_all_sources(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for d in self._docs:
            s = d.get("metadata", {}).get("source")
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def get_document_count(self) -> int:
        return len(self._docs)

    def delete_all(self) -> None:
        self._docs = []
        self._rebuild_index()
        self._persist()

    def get_all_documents(self) -> list[dict[str, Any]]:
        return [
            {"id": d["id"], "text": d["text"], "metadata": d["metadata"]}
            for d in self._docs
        ]

    def get_source_details(self) -> list[dict]:
        counts: dict[str, int] = {}
        for d in self._docs:
            src = d.get("metadata", {}).get("source", "")
            if src:
                counts[src] = counts.get(src, 0) + 1
        return [{"source": s, "chunks": c} for s, c in counts.items()]
