"use client";

import { useLang } from "@/lib/i18n";
import type { EvalReport } from "@/lib/types";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const PIPELINE: Record<string, [string, string]> = {
  "raw: bm25, package prices, no judge, no outlier filter": ["plain word search and average", "só busca por palavras e média"],
  "+ unit normalization": ["+ unit prices", "+ preço por unidade"],
  "+ judge": ["+ remove items that aren't the product", "+ remover o que não é o produto"],
  "+ outlier filter": ["+ ignore prices typed wrong", "+ ignorar preços digitados errado"],
  "+ hybrid retrieval (full pipeline)": ["+ search by words and meaning (complete)", "+ busca por palavras e sentido (completo)"],
};
const MODE: Record<string, [string, string]> = { bm25: ["by words", "por palavras"], dense: ["by meaning", "por sentido"], hybrid: ["both", "os dois"] };

export default function EvalView({ report }: { report: EvalReport | null }) {
  const { lang, t } = useLang();
  if (!report) return <div className="card empty">{t("API unreachable — start it on :8900 to see the live evaluation.")}</div>;
  const metrics = Object.keys(report.retrieval.hybrid);
  const worst = Math.max(...report.price.map((p) => p.max_ape));
  const pt = lang === "pt";

  return (
    <main className="grid">
      <section>
        <h1 style={{ font: "600 28px/1.1 var(--display)", letterSpacing: "-.03em", margin: "0 0 8px" }}>
          {t("Each step has to prove it helps")}
        </h1>
        <p className="muted" style={{ maxWidth: 760, margin: 0 }}>
          {pt
            ? `O conjunto de teste tem ${report.records} compras inventadas em que o preço certo é conhecido. Assim dá para medir o erro de verdade, sem achismo: ${report.golden_queries} buscas (com erros de digitação e sinônimos) e ${report.price_queries} perguntas de preço. Se algum número piorar, o CI falha.`
            : `The test set has ${report.records} made-up purchases where the right price is known, so the error is measured instead of guessed: ${report.golden_queries} searches (with typos and synonyms) and ${report.price_queries} price questions. If any number gets worse, CI fails.`}
        </p>
      </section>

      <section className="card">
        <header><span className="label">{t("Price error, step by step")}</span><span className="muted">{t("how far the typical price lands from the true price")}</span></header>
        <table>
          <thead><tr><th>{t("Steps on")}</th><th>{t("Typical error")}</th><th>{t("Worst error")}</th><th style={{ width: "30%" }}></th><th>{t("Within 10%")}</th></tr></thead>
          <tbody>
            {report.price.map((p, i) => {
              const label = PIPELINE[p.pipeline]?.[pt ? 1 : 0] ?? p.pipeline;
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
        <header><span className="label">{t("Search quality")}</span><span className="muted">{t("a result counts as right when it's the same kind of product")}</span></header>
        <table>
          <thead><tr><th>{t("Search type")}</th>{metrics.map((m) => <th key={m}>{m}</th>)}</tr></thead>
          <tbody>
            {Object.entries(report.retrieval).map(([mode, m]) => (
              <tr key={mode}><td>{MODE[mode]?.[pt ? 1 : 0] ?? mode}</td>{metrics.map((k) => <td key={k} className="mono">{m[k].toFixed(3)}</td>)}</tr>
            ))}
          </tbody>
        </table>
        <div className="body muted" style={{ fontSize: 13 }}>
          {pt
            ? "A busca por sentido acerta tudo aqui porque as descrições de teste seguem modelos fixos. Em dados reais, a busca por palavras pega detalhes como \"85a\", \"i5\" ou \"75g\" que a busca por sentido perde. Por isso o sistema usa as duas juntas."
            : "Search by meaning gets everything right here because the test descriptions follow fixed templates. On real data, word search catches details like \"85a\", \"i5\" or \"75g\" that meaning search misses. That's why the app combines both."}
        </div>
      </section>
    </main>
  );
}
