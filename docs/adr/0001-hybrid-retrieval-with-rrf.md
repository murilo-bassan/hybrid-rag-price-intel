# ADR 0001 — Hybrid retrieval fused with RRF

**Status:** accepted

## Context
Purchase descriptions mix spec tokens that must match exactly ("85a", "i5",
"75g/m²") with free text full of typos, abbreviations and casing noise
("COMPUTADOR ORTÁTIL", "c/", "p/"). BM25 wins the first, dense retrieval the second.

## Decision
Run both and fuse with Reciprocal Rank Fusion (`k = 60`). RRF uses ranks only,
so BM25 scores and cosine similarities never need calibrating against each other.
The dense arm uses an offline `HashingEmbedder` (signed hashed char 3/4-grams)
behind an `Embedder` protocol; `PgVectorIndex` stores the same vectors in
Postgres with an HNSW cosine index and is tested to agree with the in-memory index.

## Consequences
- Works with no model downloads or keys; a real embedding model is a drop-in.
- On the synthetic set dense alone scores 1.0 — the descriptions come from
  templates. The evaluation page says so instead of hiding it; hybrid is kept for
  open-vocabulary data, and both arms stay measured.
