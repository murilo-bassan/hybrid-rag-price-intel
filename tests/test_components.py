import json
import os
import re

import httpx
import numpy as np
import pytest

from priceintel import data, stats, text, units
from priceintel.index import BM25, DenseIndex, HashingEmbedder, PgVectorIndex, rrf
from priceintel.judge import LLMJudge, RuleJudge


def test_synthetic_data_is_deterministic_and_has_truth():
    rows = data.records()
    assert len(rows) == 3200 and rows == data.records.__wrapped__()
    assert {"_category", "_true_base_price"} <= set(rows[0])
    assert "_category" not in data.public(rows[0])
    assert 0.01 < sum(1 for r in rows if r["_entry_error"]) / len(rows) < 0.06


@pytest.mark.parametrize("package, unit, factor", [
    ("UN", "un", 1), ("CX C/ 10", "un", 10), ("FARDO C/ 12", "un", 12), ("PCT 500G", "kg", 0.5),
    ("PCT 1KG", "kg", 1), ("RESMA 500 FL", "resma", 1), ("CX C/ 10 RESMAS", "resma", 10), ("cx c/50", "un", 50),
])
def test_unit_normalization(package, unit, factor):
    n = units.normalize(package)
    assert (n.base_unit, n.factor) == (unit, factor)


def test_every_synthetic_package_normalizes_to_its_truth():
    for p in data.CATALOG:
        for label, factor in p.packages:
            assert units.normalize(label).factor == factor, (p.category, label)


def test_text_normalization():
    assert text.tokens("CAFÉ TORRADO E MOÍDO c/ 500g") == ["cafe", "torrado", "moido", "500g"]
    assert text.stem("notebooks") == "notebook" and text.stem("impressoes") == "impressao"
    assert "notebook" in text.expand(["laptop"])


def test_bm25_prefers_exact_terms():
    idx = BM25(["toner hp 85a preto", "toner hp 12a preto", "papel a4"])
    assert idx.search("toner 85a")[0][0] == 0


def test_dense_tolerates_typos():
    docs = ["cadeira giratoria com bracos", "mesa para escritorio", "caneta azul"]
    idx = DenseIndex(docs, HashingEmbedder())
    assert idx.search("cadera giratoria")[0][0] == 0


def test_embeddings_are_normalized():
    v = HashingEmbedder(64).embed(["abc def", ""])
    assert np.isclose(np.linalg.norm(v[0]), 1) and np.linalg.norm(v[1]) == 0


def test_rrf_rewards_agreement():
    fused = rrf([[(1, 9.0), (2, 8.0), (3, 7.0)], [(3, 0.9), (1, 0.8), (4, 0.7)]])
    assert [d for d, _ in fused][:2] == [1, 3]


@pytest.mark.parametrize("query, desc, keep", [
    ("computador", "Mesa para computador 120x60cm", False),
    ("computador", "Computador desktop Core i5 8GB", True),
    ("notebook", "SUPORTE P/ NOTEBOOK REGULAVEL", False),
    ("notebook", "Notebook 14 pol Ryzen 5", True),
    ("mouse", "Mouse pad tecido 22x18cm", False),
    ("mouse", "MOUSE OPTICO C/ FIO USB", True),
    ("cafe", "Filtro de papel para café 103", False),
    ("cafe", "Café torrado e moído tradicional", True),
])
def test_rule_judge(query, desc, keep):
    assert RuleJudge().judge(query, [desc])[0].keep is keep


def test_llm_judge_batches_and_falls_back():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        n = len(re.findall(r"^\d+\. ", body["messages"][1]["content"], re.M))
        if len(calls) == 2:
            return httpx.Response(500)
        verdicts = [{"i": i, "keep": i % 2 == 0, "reason": "llm"} for i in range(n)]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"verdicts": verdicts})}}]})

    judge = LLMJudge("https://llm.example", "k", "m", batch=3, transport=httpx.MockTransport(handler))
    out = judge.judge("mouse", ["Mouse USB", "Mouse pad", "Mouse sem fio", "Mouse pad gel", "Mouse óptico"])
    assert len(out) == 5 and len(calls) == 2
    assert [v.reason for v in out[:3]] == ["llm"] * 3
    assert all("rule fallback" in v.reason for v in out[3:])   # second batch failed → rules
    assert out[3].keep is False and out[4].keep is True


def test_robust_stats_drop_multiplicative_outliers():
    prices = [10, 11, 9.5, 10.4, 10.2, 101, 1.02, 9.9]
    s = stats.robust(prices)
    assert set(s.outliers) == {5, 6}
    assert 9.8 < s.median < 10.4 and not s.low_confidence


def test_small_sample_is_flagged():
    assert stats.robust([10, 11, 12]).low_confidence
    assert stats.robust([]).median is None


PG = os.environ.get("TEST_PGVECTOR_URL", "postgresql://rag:rag@localhost:55433/rag")


def test_pgvector_matches_in_memory_index():
    psycopg = pytest.importorskip("psycopg")
    try:
        psycopg.connect(PG, connect_timeout=3).close()
    except psycopg.OperationalError:
        pytest.skip("pgvector not reachable — docker compose up -d pgvector")
    docs = [r["description"] for r in data.records()[:400]]
    emb = HashingEmbedder()
    pg, mem = PgVectorIndex(PG, docs, emb), DenseIndex(docs, emb)
    try:
        for q in ("notebook i5", "papel a4", "cadera giratoria"):
            (pi, ps), (mi, ms) = pg.search(q, 5)[0], mem.search(q, 5)[0]
            assert docs[pi] == docs[mi] or abs(ps - ms) < 1e-4   # ties between identical descriptions
    finally:
        pg.close()
