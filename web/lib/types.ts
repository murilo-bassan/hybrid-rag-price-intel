export type Mode = "bm25" | "dense" | "hybrid";

export interface Item {
  id: string;
  description: string;
  package: string;
  quantity: number;
  unit_price: number;
  agency: string;
  supplier: string;
  state: string;
  date: string;
  score: number;
  comparable_price: number;
  base_unit: string;
  unit_rule: string;
  kept: boolean;
  reason: string;
  outlier: boolean;
}

export interface Stats {
  n_input: number;
  n_used: number;
  outliers: number[];
  median: number | null;
  p25: number | null;
  p75: number | null;
  mean_trimmed: number | null;
  minimum: number | null;
  maximum: number | null;
  low_confidence: boolean;
}

export interface Research {
  query: string;
  base_unit: string | null;
  judge: string | null;
  stats: Stats;
  items: Item[];
  retrieval_depth: number;
  retrieval_rounds: number;
  timings_ms: { retrieve: number; judge: number; stats: number };
}

export interface Citation {
  id: string;
  description: string;
  comparable_price: number;
  agency: string;
  date: string;
}

export interface Answer {
  route: "price_research" | "help" | "no_data";
  product?: string;
  answer: string;
  citations: Citation[];
  research?: Research;
}

export interface EvalReport {
  retrieval: Record<Mode, Record<string, number>>;
  price: { pipeline: string; median_ape: number; max_ape: number; within_10pct: string }[];
  golden_queries: number;
  price_queries: number;
  records: number;
}

export const brl = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: v < 10 ? 2 : 2 });
