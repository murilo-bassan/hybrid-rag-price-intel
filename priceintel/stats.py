"""Robust price statistics.

Prices are multiplicative (a ×10 typo is as wrong as a ÷10 one), so outliers
are detected on the log scale with Tukey fences. The headline number is the
median of what survives; the range shown is the interquartile range. With
fewer than five prices the result is marked `low_confidence` — a small sample
is reported honestly, not hidden.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PriceStats:
    n_input: int
    n_used: int
    outliers: list[int]          # positions (in the input list) removed as outliers
    median: float | None
    p25: float | None
    p75: float | None
    mean_trimmed: float | None
    minimum: float | None
    maximum: float | None
    low_confidence: bool


def robust(prices: list[float], fence: float = 1.5) -> PriceStats:
    values = np.array([p for p in prices if p > 0], dtype=float)
    if len(values) == 0:
        return PriceStats(len(prices), 0, [], None, None, None, None, None, None, True)
    logs = np.log(np.array(prices, dtype=float).clip(min=1e-9))
    q1, q3 = np.percentile(logs, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - fence * max(iqr, 0.05), q3 + fence * max(iqr, 0.05)
    keep = (logs >= lo) & (logs <= hi) & (np.array(prices) > 0)
    used = np.array(prices, dtype=float)[keep]
    outliers = [i for i, k in enumerate(keep) if not k]
    if len(used) == 0:
        return PriceStats(len(prices), 0, outliers, None, None, None, None, None, None, True)
    s = np.sort(used)
    cut = int(len(s) * 0.1)
    trimmed = s[cut:len(s) - cut] if len(s) - 2 * cut > 0 else s
    return PriceStats(
        n_input=len(prices), n_used=len(used), outliers=outliers,
        median=round(float(np.median(used)), 4), p25=round(float(np.percentile(used, 25)), 4),
        p75=round(float(np.percentile(used, 75)), 4), mean_trimmed=round(float(trimmed.mean()), 4),
        minimum=round(float(s[0]), 4), maximum=round(float(s[-1]), 4), low_confidence=len(used) < 5,
    )
