"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import PriceStrip from "@/components/PriceStrip";
import { brl, type Answer, type Mode, type Research } from "@/lib/types";
import { translateReason, useLang } from "@/lib/i18n";

const EXAMPLES = {
  en: ["How much does a computer cost?", "price of A4 paper", "coffee", "how much does a mouse cost", "cadera giratoria"],
  pt: ["Quanto custa um computador?", "preço de papel A4", "café torrado", "quanto custa um mouse?", "cadera giratoria"],
};
const MODES: [Mode, string][] = [["bm25", "by words"], ["dense", "by meaning"], ["hybrid", "both"]];

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
  const latest = useRef(0); // only the newest request may update the screen

  // a citation jumps to the purchase it cites
  const showSource = (id: string) => {
    setFocused(id);
    document.getElementById(`row-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const run = useCallback(async (q: string) => {
    const ticket = ++latest.current;
    setBusy(true);
    setError(null);
    try {
      const a: Answer = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, lang }),
      }).then((r) => r.json());
      const params = new URLSearchParams({ q: a.product ?? "", mode, judge: String(judge), normalize: String(normalize), outliers: String(outliers), k: "60" });
      const found: Research | null = a.product ? await fetch(`/api/research?${params}`).then((r) => r.json()) : null;
      if (ticket !== latest.current) return;
      setAnswer(a);
      setResearch(found);
    } catch {
      setError(t("API unreachable — start it with `uvicorn priceintel.api:app --port 8900`."));
    } finally {
      if (ticket === latest.current) setBusy(false);
    }
  }, [mode, judge, normalize, outliers, lang, t]);

  useEffect(() => { run(question); /* re-run when a pipeline switch or the language changes */ }, [mode, judge, normalize, outliers, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const s = research?.stats;
  const rejected = research?.items.filter((i) => !i.kept).length ?? 0;
  const ablated = !judge || !normalize || !outliers || mode !== "hybrid";

  return (
    <main className="grid">
      <section className="intro">
        <h1>{t("How much did the government pay?")}</h1>
        {t("Ask about any product. The search skips items that only look similar, turns boxes and packs into unit prices and ignores prices typed in wrong. Every number links to the purchases behind it.")}
      </section>

      <section className="hero">
        <div className="card">
          <div className="body stack">
            <form className="row" onSubmit={(e) => { e.preventDefault(); run(question); }}>
              <input className="input" style={{ flex: 1 }} value={question} onChange={(e) => setQuestion(e.target.value)}
                placeholder={t("Ask about a product")} aria-label="question" />
              <button className="btn primary" disabled={busy}>{busy ? t("searching…") : t("Search")}</button>
            </form>
            <div className="row">
              <span className="label">{t("Examples")}</span>
              {EXAMPLES[lang].map((ex) => (
                <button key={ex} className="btn" style={{ height: 32, padding: "0 13px", fontSize: 13.5 }} onClick={() => { setQuestion(ex); run(ex); }}>{ex}</button>
              ))}
            </div>
            {error && <div className="chip bad">{error}</div>}
            {answer && (
              <div className="answer">
                {answer.answer}
                {ablated && <div className="label" style={{ marginTop: 10, color: "var(--warn)" }}>{t("This answer uses every step. The numbers below follow your switches.")}</div>}
                {answer.citations.length > 0 && (
                  <div className="row" style={{ marginTop: 12, gap: 4 }}>
                    <span className="label" style={{ marginRight: 4 }}>{t("Based on")}</span>
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
          <header><span className="label">{t("Try turning a step off")}</span>{ablated && <span className="chip warn">{t("step off")}</span>}</header>
          <div className="body stack" style={{ gap: 14 }}>
            <div className="stack" style={{ gap: 6 }}>
              <span className="label">{t("Search")}</span>
              <div className="seg">
                {MODES.map(([m, label]) => (
                  <button key={m} data-on={mode === m} onClick={() => setMode(m)}>{t(label)}</button>
                ))}
              </div>
            </div>
            <label className="toggle"><input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} /> {t("Convert boxes and packs to unit price")}</label>
            <label className="toggle"><input type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} /> {t("Remove items that aren't the product")}</label>
            <label className="toggle"><input type="checkbox" checked={outliers} onChange={(e) => setOutliers(e.target.checked)} /> {t("Ignore prices typed in wrong")}</label>
            <p className="muted" style={{ margin: 0, fontSize: 13.5 }}>
              {t("Turn a step off and watch the estimate get worse. The Evaluation page measures this on test data.")}
            </p>
          </div>
        </aside>
      </section>

      {research && s && (
        <>
          <section className="kpis">
            <div className="kpi"><div className="label">{t("Typical price")} / {research.base_unit}</div><div className="v accent">{brl(s.median)}</div></div>
            <div className="kpi"><div className="label">{t("Most paid between")}</div><div className="v" style={{ fontSize: 22 }}>{brl(s.p25)} – {brl(s.p75)}</div></div>
            <div className="kpi"><div className="label">{t("Purchases used")}</div><div className="v">{s.n_used}<small>{t("of")} {research.items.length} {t("found")}</small></div></div>
            <div className="kpi"><div className="label">{t("Set aside")}</div><div className="v">{rejected + s.outliers.length}<small>{rejected} {t("not the product")} · {s.outliers.length} {t("typed wrong")}</small></div></div>
          </section>

          <section className="card">
            <header>
              <span className="label">{t("Every price found")}</span>
              <span className="row">
                <span className="chip ok">{t("used")}</span><span className="chip bad">{t("typed wrong")}</span><span className="chip">{t("not the product")}</span>
              </span>
            </header>
            <div className="body"><PriceStrip items={research.items} stats={s} unit={research.base_unit} /></div>
          </section>

          <section className="card scroll">
            <header><span className="label">{t("Purchases found")}</span><span className="muted">{research.items.length}</span></header>
            <table>
              <thead><tr><th>{t("Record")}</th><th>{t("Description")}</th><th>{t("Package")}</th><th>{t("Price paid")}</th><th>{t("per")} {research.base_unit}</th><th>{t("State")}</th><th>{t("Result")}</th></tr></thead>
              <tbody>
                {[...research.items]
                  .sort((a, b) => Number(!a.kept) * 2 + Number(a.outlier) - (Number(!b.kept) * 2 + Number(b.outlier)))
                  .slice(0, 25).map((it) => (
                  <tr key={it.id} id={`row-${it.id}`} className={[it.kept && !it.outlier ? "" : "dim", focused === it.id ? "focused" : ""].join(" ").trim() || undefined}>
                    <td className="mono muted">{it.id}</td>
                    <td>{it.description}<div className="muted" style={{ fontSize: 12.5 }}>{it.agency} · {it.date}</div></td>
                    <td className="mono">{it.package}</td>
                    <td className="mono">{brl(it.unit_price)}</td>
                    <td className="mono">{brl(it.comparable_price)}</td>
                    <td>{it.state}</td>
                    <td>{!it.kept ? <span className="chip">{translateReason(it.reason, t)}</span> : it.outlier ? <span className="chip bad">{t("typed wrong")}</span> : <span className="chip ok">{t("used")}</span>}</td>
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
