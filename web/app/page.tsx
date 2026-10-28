"use client";

import { useCallback, useEffect, useState } from "react";
import PriceStrip from "@/components/PriceStrip";
import { brl, type Answer, type Mode, type Research } from "@/lib/types";
import { translateReason, useLang } from "@/lib/i18n";

const EXAMPLES = {
  en: ["How much does a computer cost?", "price of A4 paper", "coffee", "how much does a mouse cost", "cadera giratoria"],
  pt: ["Quanto custa um computador?", "preço de papel A4", "café torrado", "quanto custa um mouse?", "cadera giratoria"],
};

export default function Home() {
  const { lang, t } = useLang();
  const [question, setQuestion] = useState(EXAMPLES.pt[0]);
  const [mode, setMode] = useState<Mode>("hybrid");
  const [judge, setJudge] = useState(true);
  const [normalize, setNormalize] = useState(true);
  const [outliers, setOutliers] = useState(true);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [research, setResearch] = useState<Research | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState<string | null>(null);

  // a citation jumps to the purchase it cites
  const showSource = (id: string) => {
    setFocused(id);
    document.getElementById(`row-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const run = useCallback(async (q: string) => {
    setBusy(true);
    setError(null);
    try {
      const a: Answer = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, lang }),
      }).then((r) => r.json());
      setAnswer(a);
      if (a.product) {
        const params = new URLSearchParams({ q: a.product, mode, judge: String(judge), normalize: String(normalize), outliers: String(outliers), k: "60" });
        setResearch(await fetch(`/api/research?${params}`).then((r) => r.json()));
      } else setResearch(null);
    } catch {
      setError(t("API unreachable — start it with `uvicorn priceintel.api:app --port 8900`."));
    } finally {
      setBusy(false);
    }
  }, [mode, judge, normalize, outliers, lang, t]);

  useEffect(() => { run(question); /* re-run when a pipeline switch or the language changes */ }, [mode, judge, normalize, outliers, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const s = research?.stats;
  const rejected = research?.items.filter((i) => !i.kept).length ?? 0;
  const ablated = !judge || !normalize || !outliers || mode !== "hybrid";

  return (
    <main className="grid">
      <section className="hero">
        <div className="card">
          <div className="body stack">
            <form className="row" onSubmit={(e) => { e.preventDefault(); run(question); }}>
              <input className="input" style={{ flex: 1 }} value={question} onChange={(e) => setQuestion(e.target.value)}
                placeholder={t("Ask a price question — PT or EN")} aria-label="question" />
              <button className="btn primary" disabled={busy}>{busy ? t("researching…") : t("Research ▸")}</button>
            </form>
            <div className="row">
              <span className="label">{t("try")}</span>
              {EXAMPLES[lang].map((ex) => (
                <button key={ex} className="btn" style={{ height: 28 }} onClick={() => { setQuestion(ex); run(ex); }}>{ex}</button>
              ))}
            </div>
            {error && <div className="chip bad">{error}</div>}
            {answer && (
              <div className="answer">
                {answer.answer}
                {answer.citations.length > 0 && (
                  <div className="row" style={{ marginTop: 10 }}>
                    <span className="label">{t("sources")}</span>
                    {answer.citations.map((c) => (
                      <button key={c.id} type="button" className="cite" onClick={() => showSource(c.id)}
                        title={`${c.description} · ${c.agency} · ${c.date}`}>{c.id} · {brl(c.comparable_price)}</button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <aside className="card">
          <header><span className="label">{t("pipeline switches")}</span>{ablated && <span className="chip warn">{t("ablated")}</span>}</header>
          <div className="body stack">
            <div className="stack" style={{ gap: 6 }}>
              <span className="label">{t("retrieval")}</span>
              <div className="seg">
                {(["bm25", "dense", "hybrid"] as Mode[]).map((m) => (
                  <button key={m} data-on={mode === m} onClick={() => setMode(m)}>{m}</button>
                ))}
              </div>
            </div>
            <label className="toggle"><input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} /> {t("normalize packages → base unit")}</label>
            <label className="toggle"><input type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} /> {t("judge: drop what isn’t the product")}</label>
            <label className="toggle"><input type="checkbox" checked={outliers} onChange={(e) => setOutliers(e.target.checked)} /> {t("log-scale outlier fences")}</label>
            <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>
              {t("Switch stages off to watch the estimate break — the same ablation is measured on the evaluation page.")}
            </p>
          </div>
        </aside>
      </section>

      {research && s && (
        <>
          <section className="kpis">
            <div className="kpi"><div className="label">{t("median")} / {research.base_unit}</div><div className="v accent">{brl(s.median)}</div></div>
            <div className="kpi"><div className="label">{t("interquartile range")}</div><div className="v" style={{ fontSize: 20 }}>{brl(s.p25)} – {brl(s.p75)}</div></div>
            <div className="kpi"><div className="label">{t("sample")}</div><div className="v">{s.n_used}<small>{t("of")} {research.items.length} {t("retrieved")}</small></div></div>
            <div className="kpi"><div className="label">{t("set aside")}</div><div className="v">{rejected}<small>{t("judge")} · {s.outliers.length} {t("outliers")}</small></div></div>
          </section>

          <section className="card">
            <header>
              <span className="label">{t("every price, comparable unit, log scale")}</span>
              <span className="row">
                <span className="chip ok">{t("used")}</span><span className="chip bad">{t("outlier")}</span><span className="chip">{t("judge rejected")}</span>
                <span className="mono muted">{t("depth")} {research.retrieval_depth} · {research.retrieval_rounds} {t(research.retrieval_rounds > 1 ? "rounds" : "round")} · {research.timings_ms.retrieve + research.timings_ms.judge + research.timings_ms.stats} ms</span>
              </span>
            </header>
            <div className="body"><PriceStrip items={research.items} stats={s} unit={research.base_unit} /></div>
          </section>

          <section className="card scroll">
            <header><span className="label">{t("retrieved purchases")}</span><span className="mono muted">{t("judge")}: {research.judge ?? t("off")}</span></header>
            <table>
              <thead><tr><th>{t("id")}</th><th>{t("description")}</th><th>{t("package")}</th><th>{t("paid")}</th><th>{t("per")} {research.base_unit}</th><th>{t("state")}</th><th>{t("verdict")}</th></tr></thead>
              <tbody>
                {[...research.items]
                  .sort((a, b) => Number(!a.kept) * 2 + Number(a.outlier) - (Number(!b.kept) * 2 + Number(b.outlier)))
                  .slice(0, 25).map((it) => (
                  <tr key={it.id} id={`row-${it.id}`} className={[it.kept && !it.outlier ? "" : "dim", focused === it.id ? "focused" : ""].join(" ").trim() || undefined}>
                    <td className="mono">{it.id}</td>
                    <td>{it.description}<div className="mono muted" style={{ fontSize: 11 }}>{it.agency} · {it.date}</div></td>
                    <td className="mono">{it.package}</td>
                    <td className="mono">{brl(it.unit_price)}</td>
                    <td className="mono">{brl(it.comparable_price)}</td>
                    <td className="mono">{it.state}</td>
                    <td>{!it.kept ? <span className="chip">{translateReason(it.reason, t)}</span> : it.outlier ? <span className="chip bad">{t("outlier")}</span> : <span className="chip ok">{t("used")}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </main>
  );
}
