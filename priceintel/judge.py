"""The judge: removes from the sample what is *not* the product.

Retrieval answers "what looks like this query?". Price research needs "what
IS this product?". Without a judge, "computador" brings tables for computers
and the median comes out wrong. The judge sees the query and a batch of
candidate descriptions and returns keep/reject with a reason per item.

`RuleJudge` is offline and explainable (accessory patterns, head-noun
position). `LLMJudge` asks any OpenAI-compatible model the same question in
batches with a JSON schema; it falls back to the rule judge on any failure, so
a model outage degrades quality, never availability.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from priceintel.text import fold, stem

# "X para <head>", "suporte/capa/mesa ... <head>": the item is an accessory of the head product.
_ACCESSORY = re.compile(r"\b(para|p/|p)\s+(?:o |a )?(\w+)")
_ACCESSORY_NOUNS = {"suporte", "capa", "mochila", "mesa", "base", "filtro", "coador", "pad", "mousepad", "cabo",
                    "carregador", "pelicula", "bolsa", "estojo", "refil"}
_COMPOUND_SUFFIX = ("pad", "case", "bag")      # "mouse pad", "notebook case"
# Product families whose names overlap: asking for one must not return the other.
_EXCLUDES = {"computador": {"notebook", "portatil", "laptop"}, "microcomputador": {"notebook", "portatil"}}


@dataclass(frozen=True)
class Verdict:
    keep: bool
    reason: str


class Judge(Protocol):
    name: str

    def judge(self, query: str, descriptions: list[str]) -> list[Verdict]: ...


class RuleJudge:
    name = "rules-v1"

    def judge(self, query: str, descriptions: list[str]) -> list[Verdict]:
        from priceintel.index import head_terms
        heads = set(head_terms(query))
        out = []
        for desc in descriptions:
            f = fold(desc)
            words = [stem(w) for w in re.findall(r"[a-z0-9]+", f)]
            first = words[0] if words else ""
            if first in _ACCESSORY_NOUNS and first not in heads:
                out.append(Verdict(False, f"accessory: '{first}'"))
                continue
            compound = next((w for h in heads for w in _COMPOUND_SUFFIX if re.search(rf"\b{h}\s*{w}\b", f)), None)
            if compound:
                out.append(Verdict(False, f"accessory: '{compound}'"))
                continue
            clash = next((w for h in heads for w in _EXCLUDES.get(h, ()) if w in f and w not in heads), None)
            if clash:
                out.append(Verdict(False, f"different product family: '{clash}'"))
                continue
            m = _ACCESSORY.search(f)
            if m and stem(m.group(2)) in heads and first not in heads:
                out.append(Verdict(False, f"item is *for* a {m.group(2)}, not one"))
                continue
            if heads and not (heads & set(words)) and not any(h[:5] in f for h in heads):
                out.append(Verdict(False, "does not mention the product"))
                continue
            out.append(Verdict(True, "matches the product"))
        return out


class LLMJudge:
    name = "llm"

    def __init__(self, base_url: str, api_key: str, model: str, batch: int = 25,
                 transport: httpx.BaseTransport | None = None) -> None:
        self.model, self.batch = model, batch
        self.fallback = RuleJudge()
        self._http = httpx.Client(base_url=base_url, timeout=60, transport=transport,
                                  headers={"Authorization": f"Bearer {api_key}"})

    def _ask(self, query: str, items: list[str]) -> list[Verdict]:
        listing = "\n".join(f"{i}. {d}" for i, d in enumerate(items))
        r = self._http.post("/chat/completions", json={
            "model": self.model, "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You decide whether each purchased item IS the product the user is "
                 "pricing (not an accessory, part, or a different product). Reply as JSON: "
                 '{"verdicts": [{"i": 0, "keep": true, "reason": "..."}]} with one entry per item.'},
                {"role": "user", "content": f"Product: {query}\nItems:\n{listing}"}]})
        r.raise_for_status()
        data = json.loads(r.json()["choices"][0]["message"]["content"])
        by_i = {v["i"]: Verdict(bool(v["keep"]), str(v.get("reason", ""))) for v in data["verdicts"]}
        if set(by_i) != set(range(len(items))):
            raise ValueError("judge skipped items")
        return [by_i[i] for i in range(len(items))]

    def judge(self, query: str, descriptions: list[str]) -> list[Verdict]:
        out: list[Verdict] = []
        for start in range(0, len(descriptions), self.batch):
            chunk = descriptions[start:start + self.batch]
            try:
                out += self._ask(query, chunk)
            except Exception as e:  # degrade, don't fail
                out += [Verdict(v.keep, f"{v.reason} (rule fallback: {type(e).__name__})")
                        for v in self.fallback.judge(query, chunk)]
        return out
