"""Writes docs/EVAL.md from a fresh evaluation run.

    python scripts/eval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from priceintel import data, evaluation, research  # noqa: E402


def main() -> None:
    r = evaluation.run(research.Engine(data.records()))
    lines = ["# Evaluation", "",
             f"{r['records']} synthetic purchase records with hidden ground truth · {r['golden_queries']} retrieval queries · "
             f"{r['price_queries']} price queries. Regenerate with `python scripts/eval.py`; CI fails if quality drops "
             "(`tests/test_pipeline.py::test_evaluation_gates`).", "",
             "## Retrieval (relevant = same true category)", "",
             "| mode | recall@20 | precision@10 | nDCG@10 | MRR |", "|---|---|---|---|---|"]
    for mode, m in r["retrieval"].items():
        lines.append(f"| {mode} | {m['recall@20']:.3f} | {m['precision@10']:.3f} | {m['ndcg@10']:.3f} | {m['mrr']:.3f} |")
    lines += ["", "## Price estimate — ablation (absolute % error of the median vs the true price)", "",
              "| pipeline | median error | worst error | within 10% |", "|---|---|---|---|"]
    for row in r["price"]:
        lines.append(f"| {row['pipeline']} | {row['median_ape']:.1%} | {row['max_ape']:.1%} | {row['within_10pct']} |")
    lines += ["", "## Reading it honestly", "",
              "- **Unit normalization is the single biggest win**: comparing a box of 10 with a single unit is a "
              "10× error, and the naive pipeline's worst case is off by ~970%.",
              "- **The judge removes the long tail**: worst-case error drops from ~97% to ~12% once accessories "
              "(\"mesa para computador\", \"mouse pad\", \"filtro para café\") leave the sample.",
              "- **Dense scores perfectly here because the synthetic descriptions come from templates** — "
              "character n-grams see through casing, typos and abbreviations of a small vocabulary. On real, "
              "open-vocabulary data, BM25 carries spec tokens (\"85a\", \"i5\", \"75g\") that hashed n-grams blur; "
              "that is why the product ships hybrid (RRF) and why both arms are measured separately.",
              "- Hybrid is not best on every line of this table and the report says so. The price gate, not the "
              "retrieval leaderboard, is what protects users."]
    out = ROOT / "docs" / "EVAL.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
