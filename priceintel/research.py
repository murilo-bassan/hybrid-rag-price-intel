"""Price research: retrieve → judge → normalize units → robust statistics → grounded answer."""
from __future__ import annotations

import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from priceintel import data, stats, units
from priceintel.index import BM25, DenseIndex, HashingEmbedder, rrf
from priceintel.judge import Judge, LLMJudge, RuleJudge
from priceintel.text import fold, tokens

Mode = Literal["bm25", "dense", "hybrid"]
MIN_DENSE_SIM = 0.35


@dataclass
class Options:
    mode: Mode = "hybrid"
    k: int = 60
    judge: bool = True
    normalize_units: bool = True
    remove_outliers: bool = True
    state: str | None = None


@dataclass
class Engine:
    records: tuple[dict, ...]
    judge_impl: Judge = field(default_factory=RuleJudge)

    def __post_init__(self) -> None:
        texts = [r["description"] for r in self.records]
        self.bm25 = BM25(texts)
        self.dense = DenseIndex(texts, HashingEmbedder())

    def search(self, query: str, mode: Mode = "hybrid", k: int = 60) -> list[tuple[int, float]]:
        if mode == "bm25":
            return self.bm25.search(query, k)
        if mode == "dense":
            return self.dense.search(query, k)
        return rrf([self.bm25.search(query, k * 2), self.dense.search(query, k * 2)], limit=k)

    MIN_SAMPLE = 20
    MAX_DEPTH = 1000

    def research(self, query: str, opts: Options | None = None) -> dict[str, Any]:
        opts = opts or Options()
        t0 = time.perf_counter()
        depth, rounds = opts.k, 0
        judge_ms = 0.0
        while True:
            # Adaptive depth: when the judge rejects most of what retrieval found
            # ("computador" → tables for computers), look deeper instead of
            # reporting a tiny sample.
            rounds += 1
            hits = self.search(query, opts.mode, depth)
            rows = [dict(self.records[i], _score=s) for i, s in hits]
            if opts.state:
                rows = [r for r in rows if r["state"] == opts.state.upper()]
            tj = time.perf_counter()
            verdicts = (self.judge_impl.judge(query, [r["description"] for r in rows]) if opts.judge
                        else [None] * len(rows))
            judge_ms += (time.perf_counter() - tj) * 1000
            kept_n = sum(1 for v in verdicts if v is None or v.keep)
            if not opts.judge or kept_n >= self.MIN_SAMPLE or len(hits) < depth or depth >= self.MAX_DEPTH:
                break
            depth = min(depth * 3, self.MAX_DEPTH)
        t_search = time.perf_counter() - judge_ms / 1000
        t_judge = time.perf_counter()

        items = []
        for r, v in zip(rows, verdicts):
            if opts.normalize_units:
                price, norm = units.unit_price(r["unit_price"], r["package"])
                base_unit, rule = norm.base_unit, norm.rule
            else:
                price, base_unit, rule = r["unit_price"], "package", "not normalized"
            items.append({**data.public(r), "score": round(r["_score"], 5), "comparable_price": round(price, 4),
                          "base_unit": base_unit, "unit_rule": rule,
                          "kept": True if v is None else v.keep, "reason": "judge off" if v is None else v.reason,
                          "outlier": False, "_truth": r["_category"], "_error": r["_entry_error"]})

        kept = [it for it in items if it["kept"]]
        unit = Counter(it["base_unit"] for it in kept).most_common(1)[0][0] if kept else None
        for it in kept:
            if it["base_unit"] != unit:
                it["kept"], it["reason"] = False, f"different unit ({it['base_unit']} vs {unit})"
        kept = [it for it in items if it["kept"]]
        prices = [it["comparable_price"] for it in kept]
        result = stats.robust(prices, fence=1.5 if opts.remove_outliers else 1e9)
        for pos in result.outliers:
            kept[pos]["outlier"] = True
        t_end = time.perf_counter()

        return {
            "query": query, "options": opts.__dict__, "base_unit": unit, "judge": self.judge_impl.name if opts.judge else None,
            "stats": result.__dict__, "items": items, "retrieval_depth": depth, "retrieval_rounds": rounds,
            "timings_ms": {"retrieve": round((t_search - t0) * 1000, 2), "judge": round(judge_ms, 2),
                           "stats": round((t_end - t_judge) * 1000, 2)},
        }


_QUESTION = re.compile(r"^(quanto (custa|custou|sai|pagaram|pagou)( por)?|qual (o|e o) (preco|valor)( medio| de referencia)?( de| do| da| para)?"
                       r"|how much (does|did|is)( an?| the)?|price of|preco (de|do|da)|valor (de|do|da)|pesquisa de preco( de| do| da)?)\s*", re.I)


def extract_product(question: str) -> str:
    q = fold(question).strip(" ?!.")
    q = _QUESTION.sub("", q)
    q = re.sub(r"\b(cost|costs|custa|pagaram|no estado de \w+|em \w{2}$|um|uma|o|a)\b", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def _brl(v: float, lang: str) -> str:
    s = f"{v:,.2f}"
    return "R$ " + (s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "pt" else s)


UNIT_PT = {"un": "unidade", "kg": "kg", "l": "litro", "resma": "resma"}


def ask(engine: Engine, question: str, state: str | None = None, lang: str = "en") -> dict[str, Any]:
    """Grounded answer: every number comes from the research result and cites record ids. `lang`: "en" or "pt"."""
    pt = lang == "pt"
    product = extract_product(question)
    lexical = engine.bm25.search(product, 1)
    dense_top = engine.dense.search(product, 1)
    # Out-of-catalog guard: no shared term AND weak semantic similarity → don't invent a price.
    if len(tokens(product)) == 0 or (not lexical and (not dense_top or dense_top[0][1] < MIN_DENSE_SIM)):
        return {"route": "help", "citations": [], "answer":
                "Diga qual produto pesquisar, por exemplo “quanto custa papel A4?” ou “preço de monitor 24 polegadas”." if pt else
                "Tell me which product to price, e.g. “quanto custa papel A4?” or “price of a 24-inch monitor”."}
    r = engine.research(product, Options(state=state))
    s = r["stats"]
    if not s["median"]:
        return {"route": "no_data", "product": product, "citations": [], "research": r, "answer":
                f"Não encontrei compras comparáveis para “{product}”." if pt else f"I found no comparable purchases for “{product}”."}
    used = [it for it in r["items"] if it["kept"] and not it["outlier"]]
    closest = sorted(used, key=lambda it: abs(it["comparable_price"] - s["median"]))[:3]
    rejected = sum(1 for it in r["items"] if not it["kept"])
    unit, ids = r["base_unit"], ", ".join(c["id"] for c in closest)
    if pt:
        answer = (f"Órgãos públicos pagaram normalmente {_brl(s['median'], lang)} por {UNIT_PT.get(unit, unit)} por “{product}”. "
                  f"A maioria pagou entre {_brl(s['p25'], lang)} e {_brl(s['p75'], lang)}. A conta usa {s['n_used']} compras parecidas; "
                  f"{rejected} itens ficaram de fora por não serem o produto ou usarem outra unidade, e "
                  f"{len(s['outliers'])} preços pareciam digitados errado.")
        if s["low_confidence"]:
            answer += " Foram poucas compras, então use como referência."
    else:
        answer = (f"Public buyers usually paid {_brl(s['median'], lang)} per {unit} for “{product}”. "
                  f"Most paid between {_brl(s['p25'], lang)} and {_brl(s['p75'], lang)}. This uses {s['n_used']} similar purchases; "
                  f"{rejected} items were left out for not being the product or using another unit, and "
                  f"{len(s['outliers'])} prices looked like typos.")
        if s["low_confidence"]:
            answer += " There were only a few purchases, so treat this as a rough guide."
    return {"route": "price_research", "product": product, "answer": answer,
            "citations": [{"id": c["id"], "description": c["description"], "comparable_price": c["comparable_price"],
                           "agency": c["agency"], "date": c["date"]} for c in closest], "research": r}


@lru_cache(maxsize=1)
def default_engine() -> Engine:
    judge: Judge = RuleJudge()
    if os.environ.get("PI_JUDGE") == "llm" and os.environ.get("LLM_API_KEY"):
        judge = LLMJudge(os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"), os.environ["LLM_API_KEY"],
                         os.environ.get("PI_JUDGE_MODEL", ""))
    return Engine(data.records(), judge)
