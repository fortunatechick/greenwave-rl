// Static SVG charts, rendered at build time (no client JavaScript).
import { fmt, ticks } from "@/lib/format";
import type { Curves, Fairness, Generalisation } from "@/lib/types";
import { REGIME_LABEL } from "@/lib/types";

const SERIES_COLOURS = ["var(--wave-b)", "var(--veh-bus)", "var(--amber)", "var(--veh-2w)", "var(--muted)"];

type Frame = { w: number; h: number; l: number; r: number; t: number; b: number };
const FRAME: Frame = { w: 640, h: 300, l: 52, r: 16, t: 14, b: 38 };

function scales(f: Frame, x: [number, number], y: [number, number]) {
  const sx = (v: number) => f.l + ((v - x[0]) / (x[1] - x[0] || 1)) * (f.w - f.l - f.r);
  const sy = (v: number) => f.h - f.b - ((v - y[0]) / (y[1] - y[0] || 1)) * (f.h - f.t - f.b);
  return { sx, sy };
}

function Axes({ f, x, y, xLabel, yLabel, xFmt = (v) => fmt(v, 0), yFmt = (v) => fmt(v, 0) }: {
  f: Frame; x: [number, number]; y: [number, number]; xLabel: string; yLabel: string;
  xFmt?: (v: number) => string; yFmt?: (v: number) => string;
}) {
  const { sx, sy } = scales(f, x, y);
  return (
    <g className="num" fontSize="11" fill="var(--muted)">
      {ticks(y[0], y[1], 4).map((v) => (
        <g key={`y${v}`}>
          <line x1={f.l} x2={f.w - f.r} y1={sy(v)} y2={sy(v)} stroke="var(--line)" strokeDasharray="2 4" />
          <text x={f.l - 8} y={sy(v) + 4} textAnchor="end">{yFmt(v)}</text>
        </g>
      ))}
      {ticks(x[0], x[1], 5).map((v) => (
        <text key={`x${v}`} x={sx(v)} y={f.h - f.b + 16} textAnchor="middle">{xFmt(v)}</text>
      ))}
      <line x1={f.l} x2={f.w - f.r} y1={f.h - f.b} y2={f.h - f.b} stroke="var(--line)" />
      <text x={(f.l + f.w - f.r) / 2} y={f.h - 4} textAnchor="middle">{xLabel}</text>
      <text transform={`translate(12 ${(f.t + f.h - f.b) / 2}) rotate(-90)`} textAnchor="middle">{yLabel}</text>
    </g>
  );
}

export function Legend({ items }: { items: { label: string; colour: string }[] }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted">
      {items.map((it) => (
        <li key={it.label} className="flex items-center gap-1.5">
          <span aria-hidden className="inline-block h-0.5 w-4 rounded" style={{ background: it.colour }} />
          {it.label}
        </li>
      ))}
    </ul>
  );
}

/** Learning curves: validation score against training steps, mean with a one-std band over seeds. */
export function CurveChart({ curves, labels }: { curves: Curves; labels: Record<string, string> }) {
  const keys = Object.keys(curves).filter((k) => curves[k].steps.length > 0);
  if (!keys.length) return <p className="text-sm text-muted">Learning curves pending.</p>;
  const all = keys.flatMap((k) => curves[k].mean.flatMap((m, i) => [m - curves[k].std[i], m + curves[k].std[i]]));
  const xMax = Math.max(...keys.flatMap((k) => curves[k].steps));
  const lo = Math.min(...all), hi = Math.max(...all);
  const y: [number, number] = [lo - (hi - lo) * 0.05, hi + (hi - lo) * 0.05];
  const x: [number, number] = [0, xMax];
  const { sx, sy } = scales(FRAME, x, y);
  return (
    <figure>
      <svg viewBox={`0 0 ${FRAME.w} ${FRAME.h}`} className="w-full" role="img"
        aria-label="Learning curves: validation score against training steps for each agent">
        <Axes f={FRAME} x={x} y={y} xLabel="training steps (decisions)" yLabel="validation score"
          xFmt={(v) => `${v / 1000}k`} yFmt={(v) => fmt(v, 2)} />
        {keys.map((k, i) => {
          const c = curves[k];
          const upper = c.steps.map((s, j) => `${sx(s)},${sy(c.mean[j] + c.std[j])}`);
          const lower = c.steps.map((s, j) => `${sx(s)},${sy(c.mean[j] - c.std[j])}`).reverse();
          const colour = SERIES_COLOURS[i % SERIES_COLOURS.length];
          return (
            <g key={k}>
              <polygon points={[...upper, ...lower].join(" ")} fill={colour} opacity="0.14" />
              <polyline points={c.steps.map((s, j) => `${sx(s)},${sy(c.mean[j])}`).join(" ")} fill="none"
                stroke={colour} strokeWidth="2" strokeLinejoin="round" />
            </g>
          );
        })}
      </svg>
      <Legend items={keys.map((k, i) => ({
        label: `${labels[k] ?? k} (${curves[k].n_seeds} seed${curves[k].n_seeds === 1 ? "" : "s"})`,
        colour: SERIES_COLOURS[i % SERIES_COLOURS.length],
      }))} />
    </figure>
  );
}

/** ECDF of per-vehicle waiting time for each reward design, with the fairness threshold marked. */
export function EcdfChart({ fairness, T }: { fairness: Fairness; T: number }) {
  const keys = Object.keys(fairness);
  if (!keys.length) return <p className="text-sm text-muted">Fairness distributions pending.</p>;
  const xMax = Math.max(...keys.map((k) => fairness[k].ecdf_x[fairness[k].ecdf_x.length - 1]), T * 1.2);
  const x: [number, number] = [0, xMax];
  const y: [number, number] = [0, 1];
  const { sx, sy } = scales(FRAME, x, y);
  return (
    <figure>
      <svg viewBox={`0 0 ${FRAME.w} ${FRAME.h}`} className="w-full" role="img"
        aria-label="Cumulative distribution of per-vehicle waiting time for each reward design">
        <Axes f={FRAME} x={x} y={y} xLabel="waiting time per vehicle (s)" yLabel="share of vehicles"
          yFmt={(v) => `${Math.round(v * 100)}%`} />
        <line x1={sx(T)} x2={sx(T)} y1={FRAME.t} y2={FRAME.h - FRAME.b} stroke="var(--amber)" strokeDasharray="4 4" />
        <text x={sx(T) + 6} y={FRAME.t + 12} fontSize="11" fill="var(--amber)" className="num">T = {fmt(T, 0)} s</text>
        {keys.map((k, i) => (
          <polyline key={k} fill="none" strokeWidth={k === "fair" ? 2.4 : 1.6} strokeLinejoin="round"
            stroke={SERIES_COLOURS[i % SERIES_COLOURS.length]}
            points={fairness[k].ecdf_x.map((v, j) => `${sx(v)},${sy(fairness[k].ecdf_y[j])}`).join(" ")} />
        ))}
      </svg>
      <Legend items={keys.map((k, i) => ({ label: fairness[k].label, colour: SERIES_COLOURS[i % SERIES_COLOURS.length] }))} />
    </figure>
  );
}

export type BarGroup = { label: string; bars: { key: string; value: number; err?: number; colour: string }[] };

/** Grouped vertical bars with optional one-std error whiskers. */
export function BarChart({ groups, yLabel, legend, ariaLabel, digits = 0 }: {
  groups: BarGroup[]; yLabel: string; legend: { label: string; colour: string }[]; ariaLabel: string; digits?: number;
}) {
  if (!groups.length) return <p className="text-sm text-muted">Chart pending.</p>;
  const f: Frame = { ...FRAME, b: 44 };
  const max = Math.max(...groups.flatMap((g) => g.bars.map((b) => b.value + (b.err ?? 0)))) * 1.08;
  const { sy } = scales(f, [0, 1], [0, max]);
  const inner = f.w - f.l - f.r;
  const band = inner / groups.length;
  return (
    <figure>
      <svg viewBox={`0 0 ${f.w} ${f.h}`} className="w-full" role="img" aria-label={ariaLabel}>
        <g className="num" fontSize="11" fill="var(--muted)">
          {ticks(0, max, 4).map((v) => (
            <g key={v}>
              <line x1={f.l} x2={f.w - f.r} y1={sy(v)} y2={sy(v)} stroke="var(--line)" strokeDasharray="2 4" />
              <text x={f.l - 8} y={sy(v) + 4} textAnchor="end">{fmt(v, digits)}</text>
            </g>
          ))}
          <text transform={`translate(12 ${(f.t + f.h - f.b) / 2}) rotate(-90)`} textAnchor="middle">{yLabel}</text>
        </g>
        {groups.map((g, gi) => {
          const bw = Math.min(34, (band * 0.78) / g.bars.length);
          const start = f.l + gi * band + (band - bw * g.bars.length) / 2;
          return (
            <g key={g.label}>
              {g.bars.map((b, bi) => {
                const x = start + bi * bw;
                return (
                  <g key={b.key}>
                    <rect x={x + 1} y={sy(b.value)} width={bw - 2} height={Math.max(0, f.h - f.b - sy(b.value))} rx="2" fill={b.colour}>
                      <title>{`${g.label} · ${b.key}: ${fmt(b.value, 1)}${b.err ? ` ± ${fmt(b.err, 1)}` : ""}`}</title>
                    </rect>
                    {b.err ? (
                      <line x1={x + bw / 2} x2={x + bw / 2} y1={sy(b.value + b.err)} y2={sy(Math.max(0, b.value - b.err))}
                        stroke="var(--text)" strokeOpacity="0.7" />
                    ) : null}
                  </g>
                );
              })}
              <text x={f.l + gi * band + band / 2} y={f.h - f.b + 16} textAnchor="middle" fontSize="11" fill="var(--muted)">
                {g.label}
              </text>
            </g>
          );
        })}
        <line x1={f.l} x2={f.w - f.r} y1={f.h - f.b} y2={f.h - f.b} stroke="var(--line)" />
      </svg>
      <Legend items={legend} />
    </figure>
  );
}

/**
 * Generalisation heatmap: rows = trained on, columns = tested on. The colour scale diverges
 * around the diagonal mean (the regime-matched performance): worse is red, better is green.
 */
export function Heatmap({ data, unit, compact = false, showDr = true }: {
  data: Generalisation; unit: string; compact?: boolean; showDr?: boolean;
}) {
  const n = data.regimes.length;
  const diag = data.matrix.reduce((s, row, i) => s + row[i], 0) / n;
  const rows = [...data.matrix.map((row, i) => ({ label: REGIME_LABEL[data.regimes[i]] ?? data.regimes[i], row, dr: false })),
    ...(showDr && data.dr_row.length ? [{ label: "Randomised", row: data.dr_row, dr: true }] : [])];
  const spread = Math.max(...rows.flatMap((r) => r.row.map((v) => Math.abs(v - diag))), 1e-9);
  const cell = compact ? 46 : 64, left = compact ? 78 : 104, top = compact ? 34 : 42, gap = 4;
  const w = left + n * (cell + gap), h = top + rows.length * (cell * 0.72 + gap) + (showDr ? 8 : 0);
  const colour = (v: number) => {
    const d = Math.max(-1, Math.min(1, (v - diag) / spread));
    return `color-mix(in srgb, ${d > 0 ? "var(--stop)" : "var(--go)"} ${Math.round(Math.abs(d) * 62)}%, var(--surface-2))`;
  };
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-xl" role="img"
      aria-label={`Generalisation matrix of ${data.metric}: rows are the training regime, columns the test regime`}>
      <g className="num" fontSize={compact ? 10 : 11} fill="var(--muted)">
        {data.regimes.map((r, j) => (
          <text key={r} x={left + j * (cell + gap) + cell / 2} y={top - 10} textAnchor="middle">{REGIME_LABEL[r] ?? r}</text>
        ))}
        <text x={left + (n * (cell + gap)) / 2} y={11} textAnchor="middle">tested on →</text>
      </g>
      {rows.map((r, i) => {
        const y = top + i * (cell * 0.72 + gap) + (r.dr ? 8 : 0);
        return (
          <g key={r.label}>
            <text x={left - 10} y={y + cell * 0.36 + 4} textAnchor="end" fontSize={compact ? 10 : 11}
              fill={r.dr ? "var(--wave-b)" : "var(--muted)"} className="num">{r.label}</text>
            {r.row.map((v, j) => (
              <g key={j}>
                <rect x={left + j * (cell + gap)} y={y} width={cell} height={cell * 0.72} rx="5" fill={colour(v)}
                  stroke={!r.dr && i === j ? "var(--text)" : "var(--line)"} strokeOpacity={!r.dr && i === j ? 0.55 : 1}>
                  <title>{`${r.dr ? "domain randomisation" : `trained on ${data.regimes[i]}`}, tested on ${data.regimes[j]}: ${fmt(v, 1)} ${unit}`}</title>
                </rect>
                <text x={left + j * (cell + gap) + cell / 2} y={y + cell * 0.36 + 4} textAnchor="middle"
                  fontSize={compact ? 11 : 13} fill="var(--text)" className="num">{fmt(v, v >= 100 ? 0 : 1)}</text>
              </g>
            ))}
          </g>
        );
      })}
    </svg>
  );
}
