import EvalView from "@/components/EvalView";
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

// Data is fetched on the server; text and language are handled by the client view.
export default async function EvalPage() {
  return <EvalView report={await load()} />;
}
