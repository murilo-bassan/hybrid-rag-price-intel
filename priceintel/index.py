"""Lexical, dense and hybrid retrieval.

* `BM25` — exact terms, specs and model numbers ("i5", "75g", "85a").
* `HashingEmbedder` + `DenseIndex` — character n-grams hashed into a fixed
  vector: typo-tolerant ("notbook", "cadera") and fully offline. Swap in any
  real embedding model through the `Embedder` protocol; `PgVectorIndex` stores
  the same vectors in Postgres/pgvector with an HNSW index.
* `rrf` — Reciprocal Rank Fusion. It fuses *ranks*, not scores, so BM25 and
  cosine never need to be calibrated against each other.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Sequence
from typing import Protocol

import numpy as np

from priceintel.text import expand, fold, tokens


class BM25:
    def __init__(self, docs: Sequence[str], k1: float = 1.4, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.doc_tokens = [tokens(d) for d in docs]
        self.lengths = np.array([len(t) for t in self.doc_tokens], dtype=float)
        self.avgdl = float(self.lengths.mean()) if len(docs) else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for i, toks in enumerate(self.doc_tokens):
            for term, tf in Counter(toks).items():
                self.postings.setdefault(term, []).append((i, tf))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(len(self.doc_tokens))
        for term in set(expand(tokens(query))):
            for i, tf in self.postings.get(term, []):
                denom = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avgdl)
                out[i] += self.idf[term] * tf * (self.k1 + 1) / denom
        return out

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        s = self.scores(query)
        top = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in top if s[i] > 0]


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


class HashingEmbedder:
    """Character 3/4-grams + word tokens, signed-hashed into `dim` buckets, L2-normalized."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        words = tokens(text)
        expanded = expand(words)
        padded = f" {' '.join(expanded)} "
        grams = [padded[i:i + n] for n in (3, 4) for i in range(len(padded) - n + 1)]
        return grams + [f"w:{w}" for w in expanded]

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for feat in self._features(text):
                h = int.from_bytes(hashlib.blake2b(feat.encode(), digest_size=8).digest(), "little")
                out[row, h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)


class DenseIndex:
    def __init__(self, docs: Sequence[str], embedder: Embedder) -> None:
        self.embedder = embedder
        self.matrix = embedder.embed(docs)

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        q = self.embedder.embed([query])[0]
        sims = self.matrix @ q
        top = np.argsort(-sims)[:k]
        return [(int(i), float(sims[i])) for i in top]


class PgVectorIndex:
    """Same contract as `DenseIndex`, backed by pgvector (cosine distance, HNSW)."""

    def __init__(self, dsn: str, docs: Sequence[str], embedder: Embedder, table: str = "record_embeddings") -> None:
        import psycopg

        self.embedder, self.table = embedder, table
        self.conn = psycopg.connect(dsn, autocommit=True)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self.conn.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.execute(f"CREATE TABLE {table} (idx INTEGER PRIMARY KEY, embedding vector({embedder.dim}))")
        vectors = embedder.embed(docs)
        with self.conn.cursor() as cur:
            with cur.copy(f"COPY {table} (idx, embedding) FROM STDIN") as copy:
                for i, v in enumerate(vectors):
                    copy.write_row((i, "[" + ",".join(f"{x:.6f}" for x in v) + "]"))
        self.conn.execute(f"CREATE INDEX ON {table} USING hnsw (embedding vector_cosine_ops)")

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        q = "[" + ",".join(f"{x:.6f}" for x in self.embedder.embed([query])[0]) + "]"
        rows = self.conn.execute(
            f"SELECT idx, 1 - (embedding <=> %s::vector) AS sim FROM {self.table} ORDER BY embedding <=> %s::vector LIMIT %s",
            (q, q, k)).fetchall()
        return [(int(i), float(s)) for i, s in rows]

    def close(self) -> None:
        self.conn.close()


def rrf(rankings: Sequence[Sequence[tuple[int, float]]], k: int = 60, limit: int = 50) -> list[tuple[int, float]]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (doc, _) in enumerate(ranking, 1):
            fused[doc] = fused.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: -x[1])[:limit]


def head_terms(query: str) -> list[str]:
    """The query's product words (no numbers/specs), used by the judge."""
    return [t for t in expand(tokens(query)) if not any(c.isdigit() for c in t) and len(t) > 2] or [fold(query)]
