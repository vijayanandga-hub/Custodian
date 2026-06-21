"""
Retrieval (RAG)
===============

Retrieves relevant target-state patterns, BIAN service domains, and anti-pattern
definitions for a given component, so the model's recommendation is grounded in a
known corpus rather than invented.

Demo uses an in-memory cosine-similarity store over a small curated corpus. In a
real deployment this is pgvector / Bedrock Knowledge Bases. The interface
(`retrieve`) is identical, so swapping the backend is isolated to this file.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

_CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "policies" / "patterns.json"


def _embed(text: str) -> list[float]:
    """Toy hashing embedding for the offline demo (deterministic, no network).
    Replace with a real embedding model (Titan / text-embedding-3) in production."""
    vec = [0.0] * 64
    for token in text.lower().split():
        vec[hash(token) % 64] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class PatternRetriever:
    def __init__(self) -> None:
        self._docs = json.loads(_CORPUS_PATH.read_text())
        for d in self._docs:
            d["_vec"] = _embed(d["title"] + " " + d["body"])

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        qv = _embed(query)
        ranked = sorted(self._docs, key=lambda d: _cosine(qv, d["_vec"]), reverse=True)
        return [{"id": d["id"], "title": d["title"], "body": d["body"]} for d in ranked[:k]]

    def allowed_ids(self) -> set[str]:
        return {d["id"] for d in self._docs}
