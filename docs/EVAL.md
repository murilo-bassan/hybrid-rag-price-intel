# Evaluation

3200 synthetic purchase records with hidden ground truth · 25 retrieval queries · 12 price queries. Regenerate with `python scripts/eval.py`; CI fails if quality drops (`tests/test_pipeline.py::test_evaluation_gates`).

## Retrieval (relevant = same true category)

| mode | recall@20 | precision@10 | nDCG@10 | MRR |
|---|---|---|---|---|
| bm25 | 0.944 | 0.948 | 0.951 | 0.960 |
| dense | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid | 0.966 | 0.964 | 0.966 | 0.980 |

## Price estimate — ablation (absolute % error of the median vs the true price)

| pipeline | median error | worst error | within 10% |
|---|---|---|---|
| raw: bm25, package prices, no judge, no outlier filter | 23.1% | 968.7% | 4/12 |
| + unit normalization | 3.7% | 97.0% | 8/12 |
| + judge | 2.1% | 12.4% | 11/12 |
| + outlier filter | 2.0% | 12.8% | 11/12 |
| + hybrid retrieval (full pipeline) | 2.5% | 14.5% | 11/12 |

## Reading it honestly

- **Unit normalization is the single biggest win**: comparing a box of 10 with a single unit is a 10× error, and the naive pipeline's worst case is off by ~970%.
- **The judge removes the long tail**: worst-case error drops from ~97% to ~12% once accessories ("mesa para computador", "mouse pad", "filtro para café") leave the sample.
- **Dense scores perfectly here because the synthetic descriptions come from templates** — character n-grams see through casing, typos and abbreviations of a small vocabulary. On real, open-vocabulary data, BM25 carries spec tokens ("85a", "i5", "75g") that hashed n-grams blur; that is why the product ships hybrid (RRF) and why both arms are measured separately.
- Hybrid is not best on every line of this table and the report says so. The price gate, not the retrieval leaderboard, is what protects users.
