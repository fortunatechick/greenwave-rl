"use client";

import { useMemo, useState } from "react";
import { fmt } from "@/lib/format";
import type { MainRow, MetricInfo } from "@/lib/types";
import { REGIME_LABEL } from "@/lib/types";

type Props = {
  rows: MainRow[];
  regimes: string[];
  metrics: string[];
  metricInfo: Record<string, MetricInfo>;
  controllers: string[];
  labels: Record<string, string>;
  ours: string[];
  reference: string;
};

/** Main results: controllers as rows, metrics as columns, for one regime at a time. */
export function ResultsTable({ rows, regimes, metrics, metricInfo, controllers, labels, ours, reference }: Props) {
  const [regime, setRegime] = useState(regimes.includes("surge") ? "surge" : regimes[0]);
  const [sortBy, setSortBy] = useState(metrics[0]);
  const [ascending, setAscending] = useState(true);

  const table = useMemo(() => {
    const byKey = new Map<string, MainRow>();
    for (const r of rows) if (r.regime === regime) byKey.set(`${r.controller}|${r.metric}`, r);
    const present = controllers.filter((c) => metrics.some((m) => byKey.has(`${c}|${m}`)));
    const best: Record<string, number> = {};
    for (const m of metrics) {
      const values = present.map((c) => byKey.get(`${c}|${m}`)?.mean).filter((v): v is number => v !== undefined);
      if (values.length) best[m] = metricInfo[m].lowerIsBetter ? Math.min(...values) : Math.max(...values);
    }
    const sorted = [...present].sort((a, b) => {
      const va = byKey.get(`${a}|${sortBy}`)?.mean ?? Infinity;
      const vb = byKey.get(`${b}|${sortBy}`)?.mean ?? Infinity;
      return ascending ? va - vb : vb - va;
    });
    return { byKey, sorted, best };
  }, [rows, regime, controllers, metrics, metricInfo, sortBy, ascending]);

  const sort = (metric: string) => {
    if (metric === sortBy) setAscending((v) => !v);
    else {
      setSortBy(metric);
      setAscending(metricInfo[metric].lowerIsBetter);
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div role="tablist" aria-label="Demand regime" className="flex flex-wrap gap-2">
          {regimes.map((r) => (
            <button key={r} role="tab" type="button" aria-selected={regime === r} onClick={() => setRegime(r)}
              className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
                regime === r ? "border-wave-b bg-wave-b/10 text-text" : "border-line text-muted hover:text-text"
              }`}>
              {REGIME_LABEL[r] ?? r}
            </button>
          ))}
        </div>
        <label className="ml-auto flex items-center gap-2 text-sm text-muted">
          Sort by
          <select value={sortBy} onChange={(e) => sort(e.target.value)}
            className="rounded-md border border-line bg-surface-2 px-2 py-1.5 text-sm text-text">
            {metrics.map((m) => (
              <option key={m} value={m}>{metricInfo[m].label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <caption className="sr-only">
            Results in the {regime} regime: mean and standard deviation over evaluation seeds for each controller
          </caption>
          <thead>
            <tr className="border-b border-line text-xs text-muted">
              <th scope="col" className="px-4 py-3 font-medium uppercase tracking-wider">Controller</th>
              {metrics.map((m) => (
                <th key={m} scope="col" className="px-3 py-3 text-right font-medium"
                  aria-sort={sortBy === m ? (ascending ? "ascending" : "descending") : "none"}>
                  <button type="button" onClick={() => sort(m)} className="inline-flex items-center gap-1 uppercase tracking-wider hover:text-text">
                    {metricInfo[m].label}
                    <span aria-hidden className={sortBy === m ? "text-text" : "opacity-0"}>{ascending ? "↑" : "↓"}</span>
                  </button>
                  <div className="num font-normal normal-case tracking-normal">{metricInfo[m].unit}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.sorted.map((c) => (
              <tr key={c} className={`border-b border-line/60 last:border-0 ${ours.includes(c) ? "bg-wave-b/[0.06]" : ""}`}>
                <th scope="row" className="whitespace-nowrap px-4 py-2.5 font-medium">
                  {ours.includes(c) ? <span className="wave-text">{labels[c] ?? c}</span> : (labels[c] ?? c)}
                </th>
                {metrics.map((m) => {
                  const row = table.byKey.get(`${c}|${m}`);
                  const ref = table.byKey.get(`${reference}|${m}`);
                  if (!row) return <td key={m} className="num px-3 py-2.5 text-right text-muted">–</td>;
                  const info = metricInfo[m];
                  const isBest = table.best[m] !== undefined && Math.abs(row.mean - table.best[m]) < 1e-9;
                  const delta = ref && c !== reference ? row.mean - ref.mean : 0;
                  const better = info.lowerIsBetter ? delta < 0 : delta > 0;
                  const material = ref ? Math.abs(delta) > Math.abs(ref.mean) * 0.005 : false;
                  return (
                    <td key={m} className="num whitespace-nowrap px-3 py-2.5 text-right">
                      <span className={isBest ? "font-bold text-text" : ""}>{fmt(row.mean, info.digits)}</span>
                      <span className="text-muted"> ± {fmt(row.std, info.digits)}</span>
                      {material ? (
                        <span className={`ml-1 ${better ? "text-go" : "text-stop"}`}
                          title={`${better ? "better" : "worse"} than ${labels[reference] ?? reference}`}>
                          <span aria-hidden>{delta < 0 ? "↓" : "↑"}</span>
                          <span className="sr-only">{better ? "better" : "worse"} than fixed-time</span>
                        </span>
                      ) : <span className="ml-1 inline-block w-[1ch]" />}
                      {row.p_vs_fixed !== null && row.p_vs_fixed < 0.05 && c !== reference ? (
                        <span className="ml-0.5 text-text" title={`p = ${row.p_vs_fixed.toExponential(1)} vs fixed-time (Welch)`}>
                          <span aria-hidden>•</span>
                          <span className="sr-only">significant, p below 0.05</span>
                        </span>
                      ) : <span className="ml-0.5 inline-block w-[1ch]" />}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted">
        Mean ± standard deviation over evaluation seeds. <strong className="text-text">Bold</strong>: best in column.{" "}
        <span className="text-go">↓</span>/<span className="text-stop">↑</span>: better / worse than{" "}
        {labels[reference] ?? reference} in this regime. <span className="text-text">•</span>: Welch t-test against it,
        p &lt; 0.05. Click a column to sort.
      </p>
    </div>
  );
}
