# ADR 0003 — Synthetic data with a hidden ground truth, and a CI quality gate

**Status:** accepted

## Context
Real procurement data has no labels: nobody can say whether a retrieved line is
"the product" or what the "true" price was, so RAG quality usually gets eyeballed.

## Decision
Generate 3 200 records from a fixed seed where each one carries its true category,
true base-unit price and any injected entry error (`_category`, `_true_base_price`,
`_entry_error`). The pipeline never reads these fields; the API strips them
(tested). `evaluation.py` computes Recall@20, Precision@10, nDCG@10 and MRR per
retrieval mode, and the price error of every ablation. `test_evaluation_gates`
fails CI if nDCG@10 < 0.9, median error > 5% or worst error > 20%.

## Consequences
- Each stage's value is a number in `docs/EVAL.md`, not a claim.
- The generator encodes the hard parts on purpose (distractors, packages, typos,
  ×10 entry errors) so the gate would catch a regression in any of them.
- Synthetic ≠ real: the README states where the numbers are optimistic (dense recall).
