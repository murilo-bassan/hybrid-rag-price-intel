# ADR 0002 — A judge between retrieval and statistics, with adaptive depth

**Status:** accepted

## Context
Retrieval answers "what looks like this?"; price research needs "what *is*
this?". For "computador", BM25 ranks "Mesa para computador" first (short, exact
match). Averaging those gives a median of ~R$ 514 for a ~R$ 3 900 product.

## Decision
- A judge labels every retrieved item keep/reject **with a reason** before any
  statistic is computed. `RuleJudge` (offline, explainable: accessory nouns,
  "X para <produto>", compound accessories like "mouse pad", product-family
  clashes like computador vs notebook) is the default; `LLMJudge` asks any
  OpenAI-compatible model in batches with a JSON contract and **falls back to the
  rules per batch** on any failure — an outage lowers quality, never availability.
- **Adaptive depth:** if the judge leaves fewer than 20 items, retrieval goes 3×
  deeper (up to 1 000) and the judge runs again. The UI shows depth and rounds.

## Consequences
- Worst-case price error drops from ~97% to ~12% (docs/EVAL.md).
- Every exclusion is visible to the user, which is what makes the number defensible.
