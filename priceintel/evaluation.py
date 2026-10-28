"""Measured, not eyeballed: retrieval metrics and price error against the hidden ground truth.

Retrieval: for each golden query, a record is relevant iff its true category
matches. Reported per mode: Recall@20, Precision@10, nDCG@10, MRR.

Price: for each golden query, the pipeline's median vs the true base price
(averaged over states). Reported per ablation — each stage switched on in
turn — as median and worst absolute percentage error.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any

from priceintel import data
from priceintel.research import Engine, Options

GOLDEN: list[tuple[str, str]] = [
    ("notebook i5 8gb", "notebook"), ("notebook core i5", "notebook"), ("laptop", "notebook"),
    ("notbook i5", "notebook"),                                   # typo
    ("computador desktop", "desktop"), ("microcomputador", "desktop"),
    ("monitor 24 polegadas", "monitor"), ("monitor full hd", "monitor"),
    ("mouse optico usb", "mouse"), ("mouse sem fio", "mouse"),
    ("teclado abnt2", "teclado"),
    ("papel a4 75g", "papel_a4"), ("resma sulfite", "papel_a4"),
    ("cafe torrado moido", "cafe"), ("cafe em po", "cafe"),
    ("agua mineral 500ml", "agua"),
    ("cadeira giratoria", "cadeira"), ("cadera giratoria", "cadeira"),   # typo
    ("toner hp 85a", "toner"), ("detergente neutro", "detergente"), ("caneta esferografica azul", "caneta"),
    # the distractors themselves are products too: retrieval must not drown them in the head product
    ("mesa para computador", "mesa_computador"), ("suporte para notebook", "suporte_notebook"),
    ("mouse pad", "mousepad"), ("filtro de papel para cafe", "filtro_cafe"),
]

# Price queries: the product word alone, where distractors hurt most.
PRICE_GOLDEN: list[tuple[str, str]] = [
    ("notebook", "notebook"), ("computador desktop", "desktop"), ("mouse", "mouse"), ("monitor", "monitor"),
    ("papel a4", "papel_a4"), ("cafe", "cafe"), ("agua mineral", "agua"), ("cadeira giratoria", "cadeira"),
    ("toner", "toner"), ("detergente", "detergente"), ("caneta", "caneta"), ("teclado", "teclado"),
]

ABLATIONS: list[tuple[str, Options]] = [
    ("raw: bm25, package prices, no judge, no outlier filter",
     Options(mode="bm25", judge=False, normalize_units=False, remove_outliers=False)),
    ("+ unit normalization", Options(mode="bm25", judge=False, normalize_units=True, remove_outliers=False)),
    ("+ judge", Options(mode="bm25", judge=True, normalize_units=True, remove_outliers=False)),
    ("+ outlier filter", Options(mode="bm25", judge=True, normalize_units=True, remove_outliers=True)),
    ("+ hybrid retrieval (full pipeline)", Options(mode="hybrid", judge=True, normalize_units=True, remove_outliers=True)),
]


def _dcg(rels: list[int]) -> float:
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def retrieval(engine: Engine, k: int = 20) -> dict[str, dict[str, float]]:
    records = engine.records
    out = {}
    for mode in ("bm25", "dense", "hybrid"):
        rec, prec, ndcg, mrr = [], [], [], []
        for query, cat in GOLDEN:
            total = sum(1 for r in records if r["_category"] == cat)
            ranked = [records[i]["_category"] == cat for i, _ in engine.search(query, mode, 100)]
            rels = [int(x) for x in ranked]
            rec.append(sum(rels[:k]) / min(total, k))
            prec.append(sum(rels[:10]) / 10)
            ideal = _dcg([1] * min(total, 10))
            ndcg.append(_dcg(rels[:10]) / ideal if ideal else 0)
            mrr.append(next((1 / (i + 1) for i, r in enumerate(rels) if r), 0.0))
        out[mode] = {f"recall@{k}": round(sum(rec) / len(rec), 3), "precision@10": round(sum(prec) / len(prec), 3),
                     "ndcg@10": round(sum(ndcg) / len(ndcg), 3), "mrr": round(sum(mrr) / len(mrr), 3)}
    return out


def price_error(engine: Engine) -> list[dict[str, Any]]:
    rows = []
    for label, opts in ABLATIONS:
        errors = []
        for query, cat in PRICE_GOLDEN:
            truth = median(r["_true_base_price"] for r in engine.records if r["_category"] == cat)
            est = engine.research(query, Options(**{**opts.__dict__, "k": 120}))["stats"]["median"]
            errors.append(abs(est - truth) / truth if est else 1.0)
        rows.append({"pipeline": label, "median_ape": round(median(errors), 4), "max_ape": round(max(errors), 4),
                     "within_10pct": f"{sum(e <= 0.10 for e in errors)}/{len(errors)}"})
    return rows


def run(engine: Engine | None = None) -> dict[str, Any]:
    engine = engine or Engine(data.records())
    return {"retrieval": retrieval(engine), "price": price_error(engine), "golden_queries": len(GOLDEN),
            "price_queries": len(PRICE_GOLDEN), "records": len(engine.records)}
