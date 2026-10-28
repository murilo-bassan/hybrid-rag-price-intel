"""Text normalization for Portuguese procurement descriptions."""
from __future__ import annotations

import re
import unicodedata

STOP = {"de", "da", "do", "das", "dos", "e", "com", "c", "para", "p", "em", "o", "a", "os", "as", "um", "uma",
        "tipo", "ou", "similar", "marca", "referencia", "conforme", "termo", "item", "lote", "the", "of", "for"}

# Query-side expansion. Small and explicit: every entry is a decision someone can review.
SYNONYMS = {
    "laptop": ["notebook"], "portatil": ["notebook"], "pc": ["computador", "desktop"],
    "sulfite": ["papel"], "resma": ["papel"], "cafezinho": ["cafe"], "po": ["moido"],
    "agua": ["mineral"], "esferografica": ["caneta"], "cartucho": ["toner"],
}


def fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def stem(token: str) -> str:
    """Very light PT stemmer: plural and a few suffixes. Predictable beats clever here."""
    for suffix in ("coes", "oes", "aes", "ais", "eis", "res", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)] + {"coes": "cao", "oes": "ao", "aes": "ao", "ais": "al", "eis": "el",
                                             "res": "r"}.get(suffix, "")
    return token


def tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", fold(text).replace("/", " "))
    return [stem(t) for t in raw if t not in STOP and (len(t) > 1 or t.isdigit())]


def expand(query_tokens: list[str]) -> list[str]:
    out = list(query_tokens)
    for t in query_tokens:
        out += [stem(s) for s in SYNONYMS.get(t, [])]
    return out
