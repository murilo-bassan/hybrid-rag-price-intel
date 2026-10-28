"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Lang = "en" | "pt";

// English strings are the keys; PT-BR translations below.
const PT: Record<string, string> = {
  research: "pesquisa", evaluation: "avaliação", "hybrid rag · price intelligence": "rag híbrido · inteligência de preços",
  "Ask a price question — PT or EN": "Faça uma pergunta de preço — PT ou EN", "Research ▸": "Pesquisar ▸", "researching…": "pesquisando…",
  try: "teste", sources: "fontes", "pipeline switches": "etapas do pipeline", ablated: "desligada", retrieval: "busca",
  "normalize packages → base unit": "normalizar embalagens → unidade base", "judge: drop what isn’t the product": "juiz: descartar o que não é o produto",
  "log-scale outlier fences": "cercas de outlier em escala log",
  "Switch stages off to watch the estimate break — the same ablation is measured on the evaluation page.":
    "Desligue etapas para ver a estimativa quebrar — a mesma ablação é medida na página de avaliação.",
  median: "mediana", "interquartile range": "intervalo interquartil", sample: "amostra", "of": "de", retrieved: "recuperados",
  "set aside": "descartados", judge: "juiz", outliers: "outliers", "every price, comparable unit, log scale": "todos os preços, unidade comparável, escala log",
  used: "usado", outlier: "outlier", "judge rejected": "rejeitado pelo juiz", depth: "profundidade", round: "rodada", rounds: "rodadas",
  "retrieved purchases": "compras recuperadas", off: "desligado", id: "id", description: "descrição", package: "embalagem", paid: "pago",
  per: "por", state: "UF", verdict: "veredito", "API unreachable — start it with `uvicorn priceintel.api:app --port 8900`.":
    "API fora do ar — suba com `uvicorn priceintel.api:app --port 8900`.", "no comparable prices": "nenhum preço comparável",
  "measured against hidden ground truth": "medido contra gabarito oculto", "Every stage has to": "Cada etapa precisa",
  "earn its place.": "justificar sua existência.", "price estimate — ablation": "estimativa de preço — ablação",
  "absolute % error of the median vs the true price": "erro % absoluto da mediana vs o preço real", pipeline: "pipeline",
  "median error": "erro mediano", "worst error": "pior erro", "within 10%": "dentro de 10%", "relevant = same true category": "relevante = mesma categoria real",
  mode: "modo", "API unreachable — start it on :8900 to see the live evaluation.": "API fora do ar — suba na porta 8900 para ver a avaliação ao vivo.",
  "accessory": "acessório", "matches the product": "corresponde ao produto", "does not mention the product": "não menciona o produto",
  "different product family": "outra família de produto", "different unit": "unidade diferente", "judge off": "juiz desligado",
};

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (s: string) => string }>({
  lang: "en", setLang: () => {}, t: (s) => s,
});

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    let saved: string | null = null;
    try { saved = localStorage.getItem("lang"); } catch {}
    setLangState(saved === "pt" || saved === "en" ? saved : navigator.language.toLowerCase().startsWith("pt") ? "pt" : "en");
  }, []);
  useEffect(() => { document.documentElement.lang = lang === "pt" ? "pt-BR" : "en"; }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("lang", l); } catch {}
  }, []);
  const t = useCallback((s: string) => (lang === "pt" && PT[s]) || s, [lang]);
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useLang = () => useContext(Ctx);

/** Judge reasons come from the API in English ("accessory: 'mesa'"); translate the stable prefix. */
export function translateReason(reason: string, t: (s: string) => string): string {
  const [head, ...rest] = reason.split(/(?=[:(])/);
  return t(head.trim()) + (rest.length ? " " + rest.join("") : "");
}
