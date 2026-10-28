import type { Item, Stats } from "@/lib/types";
import { brl } from "@/lib/types";
import { useLang } from "@/lib/i18n";

/** Strip plot on a log scale: every comparable price as a dot, IQR band, median line.
 *  Log scale because price errors are multiplicative — a ×10 typo and a ÷10 typo sit symmetrically. */
export default function PriceStrip({ items, stats, unit }: { items: Item[]; stats: Stats; unit: string | null }) {
  const { t } = useLang();
  const sameUnit = items.filter((it) => it.base_unit === unit && it.comparable_price > 0);
  if (!sameUnit.length || stats.median == null) return <div className="empty">{t("no comparable prices")}</div>;

  const W = 760, H = 150, padX = 24, rows = { used: 48, outlier: 48, rejected: 104 };
  const values = sameUnit.map((it) => it.comparable_price);
  const lo = Math.log10(Math.min(...values) * 0.8), hi = Math.log10(Math.max(...values) * 1.25);
  const x = (v: number) => padX + ((Math.log10(v) - lo) / (hi - lo || 1)) * (W - 2 * padX);
  const jitter = (id: string) => ((parseInt(id.slice(-3), 10) * 37) % 23) - 11;
  const ticks = Array.from({ length: Math.floor(hi) - Math.ceil(lo) + 1 }, (_, i) => 10 ** (Math.ceil(lo) + i));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="price distribution">
      <rect x={x(stats.p25!)} y={24} width={Math.max(2, x(stats.p75!) - x(stats.p25!))} height={50} fill="rgba(198,255,0,.08)" stroke="rgba(198,255,0,.35)" />
      <line x1={x(stats.median)} x2={x(stats.median)} y1={16} y2={82} stroke="#c6ff00" strokeWidth={2} />
      <text x={x(stats.median) + 6} y={14} fill="#c6ff00" fontSize={11} fontFamily="JetBrains Mono, monospace">
        {t("median")} {brl(stats.median)}/{unit}
      </text>
      {ticks.map((tick) => (
        <g key={tick}>
          <line x1={x(tick)} x2={x(tick)} y1={124} y2={130} stroke="#4a4a48" />
          <text x={x(tick)} y={143} fill="#7a7a76" fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono, monospace">
            {tick >= 1000 ? `${tick / 1000}k` : tick}
          </text>
        </g>
      ))}
      <line x1={padX} x2={W - padX} y1={124} y2={124} stroke="#2a2a2a" />
      <text x={padX} y={rows.rejected + 4} fill="#4a4a48" fontSize={9.5} fontFamily="JetBrains Mono, monospace">{t("judge rejected")}</text>
      {sameUnit.map((it) => {
        const kind = !it.kept ? "rejected" : it.outlier ? "outlier" : "used";
        const fill = kind === "used" ? "#c6ff00" : kind === "outlier" ? "#ff4d5e" : "#3a3a38";
        return (
          <circle key={it.id} cx={x(it.comparable_price)} cy={rows[kind] + jitter(it.id)} r={kind === "used" ? 3.2 : 3.6}
            fill={kind === "outlier" ? "none" : fill} stroke={fill} strokeWidth={kind === "outlier" ? 1.5 : 0} opacity={kind === "used" ? 0.75 : 1}>
            <title>{`${it.id} · ${it.description} · ${brl(it.comparable_price)}/${unit} · ${it.reason}`}</title>
          </circle>
        );
      })}
    </svg>
  );
}
