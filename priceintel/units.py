"""Packaging labels → comparable units.

"CX C/ 10" means the price is for ten units; "PCT 500G" for half a kilo;
"CX C/ 10 RESMAS" for ten reams. Comparing raw prices across packages is the
most common — and most expensive — mistake in price research. Every price is
converted to a price per *base unit* before any statistic is computed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from priceintel.text import fold


@dataclass(frozen=True)
class Normalized:
    base_unit: str      # "un", "kg", "l", "resma"
    factor: float       # base units per package
    rule: str           # which rule matched — shown to the user


_RULES: list[tuple[re.Pattern[str], str, object]] = [
    (re.compile(r"cx\s*c/?\s*(\d+)\s*resmas?"), "resma", lambda m: float(m.group(1))),
    (re.compile(r"resma"), "resma", lambda m: 1.0),
    (re.compile(r"(?:pct|pacote|emb)?\s*(\d+(?:[.,]\d+)?)\s*kg"), "kg", lambda m: float(m.group(1).replace(",", "."))),
    (re.compile(r"(?:pct|pacote|emb)?\s*(\d+)\s*g\b"), "kg", lambda m: float(m.group(1)) / 1000),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*l\b"), "l", lambda m: float(m.group(1).replace(",", "."))),
    (re.compile(r"(?:cx|caixa|fardo|pct|pacote|kit)\s*c/?\s*(\d+)"), "un", lambda m: float(m.group(1))),
    (re.compile(r"^(?:un|und|unid|unidade|pc|peca)\b"), "un", lambda m: 1.0),
]


def normalize(package: str) -> Normalized:
    label = fold(package).strip()
    for pattern, unit, factor in _RULES:
        if m := pattern.search(label):
            f = factor(m)  # type: ignore[operator]
            if f > 0:
                return Normalized(unit, f, pattern.pattern)
    return Normalized("un", 1.0, "default: one unit")


def unit_price(price: float, package: str) -> tuple[float, Normalized]:
    n = normalize(package)
    return price / n.factor, n
