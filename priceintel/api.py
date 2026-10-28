"""HTTP API consumed by the Next.js app (web/).

    uvicorn priceintel.api:app --port 8900
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from priceintel import data, evaluation
from priceintel.research import Options, ask, default_engine

app = FastAPI(title="priceintel", version="0.1.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"])


def _public(result: dict[str, Any]) -> dict[str, Any]:
    """Drops ground-truth fields before anything leaves the process."""
    return {**result, "items": [{k: v for k, v in it.items() if not k.startswith("_")} for it in result["items"]]}


@app.get("/v1/research")
def research(q: str = Query(min_length=2, max_length=120), mode: Literal["bm25", "dense", "hybrid"] = "hybrid",
             judge: bool = True, normalize: bool = True, outliers: bool = True, state: str | None = None,
             k: int = Query(60, ge=10, le=300)) -> dict[str, Any]:
    opts = Options(mode=mode, k=k, judge=judge, normalize_units=normalize, remove_outliers=outliers, state=state)
    return _public(default_engine().research(q, opts))


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    state: str | None = None
    lang: Literal["en", "pt"] = "en"


@app.post("/v1/ask")
def ask_endpoint(body: AskBody) -> dict[str, Any]:
    out = ask(default_engine(), body.question, body.state, body.lang)
    if "research" in out:
        out["research"] = _public(out["research"])
    return out


@lru_cache(maxsize=1)
def _eval() -> dict[str, Any]:
    return evaluation.run(default_engine())


@app.get("/v1/eval")
def eval_report() -> dict[str, Any]:
    return _eval()


@app.get("/v1/catalog")
def catalog() -> dict[str, Any]:
    records = data.records()
    return {"records": len(records), "states": data.STATES, "agencies": len(data.AGENCIES),
            "date_range": [min(r["date"] for r in records), max(r["date"] for r in records)],
            "examples": ["notebook i5 8gb", "papel a4", "cafe", "computador desktop", "cadeira giratoria", "mouse"]}


@app.get("/health")
def health() -> dict[str, str]:
    default_engine()
    return {"status": "ok"}
