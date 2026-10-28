import type { EvalReport } from "@/lib/types";

export const dynamic = "force-dynamic";

const API = process.env.PRICEINTEL_API ?? "http://localhost:8900";

async function load(): Promise<EvalReport | null> {
  try {
    const r = await fetch(`${API}/v1/eval`, { cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch {
    return null;
  }
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export default async function EvalPage() {
  const report = await load();
  if (!report) return <div className="card empty">API unreachable — start it on :8900 to see the live evaluation.</div>;
  const metrics = Object.keys(report.retrieval.hybrid);
  const worst = Math.max(...report.price.map((p) => p.max_ape));

  return (
    <main className="grid">
      <section>
        <div className="label">measured against hidden ground truth</div>
        <h1 style={{ font: "600 34px/1.1 var(--display)", letterSpacing: "-.02em", margin: "8px 0" }}>
          Every stage has to <span className="accent">earn its place.</span>
        </h1>
        <p className="muted" style={{ maxWidth: 760 }}>
          {report.records} synthetic purchases carry their true category and true price, so retrieval quality and price error are
          computed, not guessed. {report.golden_queries} retrieval queries (typos, synonyms, distractors) · {report.price_queries} price queries.
          The same numbers gate CI.
        </p>
      </section>

      <section className="card">
        <header><span className="label">price estimate — ablation</span><span className="mono muted">absolute % error of the median vs the true price</span></header>
        <table>
          <thead><tr><th>pipeline</th><th>median error</th><th>worst error</th><th style={{ width: "34%" }}></th><th>within 10%</th></tr></thead>
          <tbody>
            {report.price.map((p, i) => (
              <tr key={p.pipeline}>
                <td>{i === report.price.length - 1 ? <b>{p.pipeline}</b> : p.pipeline}</td>
                <td className="mono">{pct(p.median_ape)}</td>
                <td className="mono" style={{ color: p.max_ape > 0.5 ? "var(--danger)" : "var(--accent)" }}>{pct(p.max_ape)}</td>
                <td><div className="bar"><i style={{ width: `${Math.max(1, (Math.log10(1 + p.max_ape * 100) / Math.log10(1 + worst * 100)) * 100)}%`, background: p.max_ape > 0.5 ? "var(--danger)" : "var(--accent)" }} /></div></td>
                <td className="mono">{p.within_10pct}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <header><span className="label">retrieval</span><span className="mono muted">relevant = same true category</span></header>
        <table>
          <thead><tr><th>mode</th>{metrics.map((m) => <th key={m}>{m}</th>)}</tr></thead>
          <tbody>
            {Object.entries(report.retrieval).map(([mode, m]) => (
              <tr key={mode}><td className="mono">{mode}</td>{metrics.map((k) => <td key={k} className="mono">{m[k].toFixed(3)}</td>)}</tr>
            ))}
          </tbody>
        </table>
        <div className="body muted" style={{ fontSize: 13 }}>
          Dense is perfect here because synthetic descriptions come from templates; on open-vocabulary data BM25 carries spec tokens
          (&quot;85a&quot;, &quot;i5&quot;, &quot;75g&quot;) that hashed n-grams blur — hence hybrid (RRF) in production, and both arms measured separately.
        </div>
      </section>
    </main>
  );
}
