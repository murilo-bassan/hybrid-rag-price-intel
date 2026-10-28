from fastapi.testclient import TestClient

from priceintel import evaluation, research
from priceintel.api import app


def test_judge_fixes_the_computer_table_problem(engine):
    without = engine.research("computador", research.Options(judge=False, k=120))
    with_judge = engine.research("computador", research.Options(judge=True, k=120))
    truth_kept = {it["_truth"] for it in with_judge["items"] if it["kept"]}
    assert truth_kept == {"desktop"}
    assert with_judge["retrieval_rounds"] >= 1 and with_judge["stats"]["n_used"] >= 20
    assert abs(with_judge["stats"]["median"] - 3900) / 3900 < 0.1
    assert abs(without["stats"]["median"] - 3900) / 3900 > abs(with_judge["stats"]["median"] - 3900) / 3900


def test_units_make_packages_comparable(engine):
    r = engine.research("papel a4 sulfite", research.Options(k=150))
    assert r["base_unit"] == "resma"
    assert abs(r["stats"]["median"] - 27) / 27 < 0.1
    raw = engine.research("papel a4 sulfite", research.Options(k=150, normalize_units=False))
    assert raw["stats"]["p75"] > r["stats"]["p75"] * 2   # boxes of 10 inflate unnormalized prices


def test_entry_errors_become_outliers(engine):
    r = engine.research("cafe torrado", research.Options(k=200))
    typos = [it for it in r["items"] if it["kept"] and it["_error"] in ("x10", "div10")]
    assert typos and all(it["outlier"] for it in typos)


def test_state_filter(engine):
    r = engine.research("monitor", research.Options(state="AM"))
    assert r["items"] and {it["state"] for it in r["items"]} == {"AM"}


def test_ask_is_grounded_and_cites(engine):
    a = research.ask(engine, "Quanto custa um notebook i5?")
    assert a["route"] == "price_research" and a["product"] == "notebook i5"
    ids = {it["id"] for it in a["research"]["items"]}
    assert len(a["citations"]) == 3 and all(c["id"] in ids for c in a["citations"])
    assert f"{a['research']['stats']['median']:,.2f}" in a["answer"]


def test_ask_refuses_out_of_catalog(engine):
    for q in ("oi", "quanto custa um foguete?"):
        assert research.ask(engine, q)["route"] == "help"


def test_evaluation_gates(engine):
    """CI gate: these thresholds fail the build if a change degrades quality."""
    report = evaluation.run(engine)
    assert report["retrieval"]["hybrid"]["ndcg@10"] >= 0.9
    full = report["price"][-1]
    raw = report["price"][0]
    assert full["median_ape"] <= 0.05 and full["max_ape"] <= 0.2
    assert raw["max_ape"] > 1.0          # the naive pipeline really is wrong, by an order of magnitude


def test_api_never_leaks_ground_truth():
    c = TestClient(app)
    r = c.get("/v1/research", params={"q": "mouse"}).json()
    assert r["items"] and not any(k.startswith("_") for k in r["items"][0])
    a = c.post("/v1/ask", json={"question": "preço de caneta azul"}).json()
    assert a["route"] == "price_research" and "_truth" not in str(a)
    assert c.get("/v1/research", params={"q": "x"}).status_code == 422
    assert c.get("/v1/eval").json()["records"] == 3200
