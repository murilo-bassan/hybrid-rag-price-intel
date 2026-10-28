"use client";

import { useLang } from "@/lib/i18n";
import type { EvalReport } from "@/lib/types";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const PIPELINE_PT: Record<string, string> = {
  "raw: bm25, package prices, no judge, no outlier filter": "bruto: bm25, preço da embalagem, sem juiz, sem filtro de outlier",
  "+ unit normalization": "+ normalização de unidade",
  "+ judge": "+ juiz",
  "+ outlier filter": "+ filtro de outliers",
  "+ hybrid retrieval (full pipeline)": "+ busca híbrida (pipeline completo)",
};

export default function EvalView({ report }: { report: EvalReport | null }) {
  const { lang, t } = useLang();
  if (!report) return <div className="card empty">{t("API unreachable — start it on :8900 to see the live evaluation.")}</div>;
  const metrics = Object.keys(report.retrieval.hybrid);
  const worst = Math.max(...report.price.map((p) => p.max_ape));
  const pt = lang === "pt";

  return (
    <main className="grid">
      <section>
        <div className="label">{t("measured against hidden ground truth")}</div>
        <h1 style={{ font: "600 34px/1.1 var(--display)", letterSpacing: "-.02em", margin: "8px 0" }}>
          {t("Every stage has to")} <span className="accent">{t("earn its place.")}</span>
        </h1>
        <p className="muted" style={{ maxWidth: 760 }}>
          {pt
            ? `${report.records} compras sintéticas carregam a categoria e o preço reais, então a qualidade da busca e o erro de preço são calculados, não chutados. ${report.golden_queries} consultas de busca (erros de digitação, sinônimos, distratores) · ${report.price_queries} consultas de preço. Os mesmos números barram o CI.`
            : `${report.records} synthetic purchases carry their true category and true price, so retrieval quality and price error are computed, not guessed. ${report.golden_queries} retrieval queries (typos, synonyms, distractors) · ${report.price_queries} price queries. The same numbers gate CI.`}
        </p>
      </section>

      <section className="card">
        <header><span className="label">{t("price estimate — ablation")}</span><span className="mono muted">{t("absolute % error of the median vs the true price")}</span></header>
        <table>
          <thead><tr><th>{t("pipeline")}</th><th>{t("median error")}</th><th>{t("worst error")}</th><th style={{ width: "34%" }}></th><th>{t("within 10%")}</th></tr></thead>
          <tbody>
            {report.price.map((p, i) => {
              const label = pt ? PIPELINE_PT[p.pipeline] ?? p.pipeline : p.pipeline;
              return (
                <tr key={p.pipeline}>
                  <td>{i === report.price.length - 1 ? <b>{label}</b> : label}</td>
                  <td className="mono">{pct(p.median_ape)}</td>
                  <td className="mono" style={{ color: p.max_ape > 0.5 ? "var(--danger)" : "var(--accent)" }}>{pct(p.max_ape)}</td>
                  <td><div className="bar"><i style={{ width: `${Math.max(1, (Math.log10(1 + p.max_ape * 100) / Math.log10(1 + worst * 100)) * 100)}%`, background: p.max_ape > 0.5 ? "var(--danger)" : "var(--accent)" }} /></div></td>
                  <td className="mono">{p.within_10pct}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="card">
        <header><span className="label">{t("retrieval")}</span><span className="mono muted">{t("relevant = same true category")}</span></header>
        <table>
          <thead><tr><th>{t("mode")}</th>{metrics.map((m) => <th key={m}>{m}</th>)}</tr></thead>
          <tbody>
            {Object.entries(report.retrieval).map(([mode, m]) => (
              <tr key={mode}><td className="mono">{mode}</td>{metrics.map((k) => <td key={k} className="mono">{m[k].toFixed(3)}</td>)}</tr>
            ))}
          </tbody>
        </table>
        <div className="body muted" style={{ fontSize: 13 }}>
          {pt
            ? "O denso acerta tudo aqui porque as descrições sintéticas vêm de templates; em dados reais de vocabulário aberto, o BM25 carrega tokens de especificação (\"85a\", \"i5\", \"75g\") que os n-gramas com hash borram — por isso o híbrido (RRF) em produção, e os dois braços medidos separadamente."
            : "Dense is perfect here because synthetic descriptions come from templates; on open-vocabulary data BM25 carries spec tokens (\"85a\", \"i5\", \"75g\") that hashed n-grams blur — hence hybrid (RRF) in production, and both arms measured separately."}
        </div>
      </section>
    </main>
  );
}
