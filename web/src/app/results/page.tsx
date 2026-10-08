import type { Metadata } from "next";
import { BarChart, CurveChart, EcdfChart, Heatmap } from "@/components/charts";
import { ResultsTable } from "@/components/ResultsTable";
import { Callout, Card, FormulaBlock, PageHeader, Section, SectionHeading } from "@/components/ui";
import {
  CONTROLLER_ORDER, OURS, ablations, controllerLabel, curves, fairness, generalisation, main, mainValue, meta, perClass,
} from "@/lib/data";
import { fmt } from "@/lib/format";
import { TEX } from "@/lib/formulas";
import { CLASS_LABEL, METRICS, REGIMES, REGIME_LABEL, TABLE_METRICS } from "@/lib/types";

export const metadata: Metadata = {
  title: "Results",
  description: "Every controller in every demand regime: waiting time, queues, throughput, fairness, generalisation and ablations.",
  alternates: { canonical: "/results/" },
};

const CLASS_COLOURS: Record<string, string> = {
  two_wheeler: "var(--veh-2w)",
  auto_rickshaw: "var(--veh-auto)",
  car: "var(--veh-car)",
  bus: "var(--veh-bus)",
};

const ABLATION_TITLES: Record<string, string> = {
  reward: "Which objective produces the best real behaviour?",
  fairness: "Without the fairness penalty, does the agent starve the minor road?",
  weighting: "Vehicle-count against passenger weighting: do buses clear faster?",
  bus_weight: "How sensitive are results to the bus occupancy assumption?",
  state: "Which observations matter?",
  interval: "Decision interval: reactivity against stability",
  sublane: "Does modelling mixed (sub-lane) traffic change the picture?",
};

export default function ResultsPage() {
  const classRegime = "peak";
  const classControllers = CONTROLLER_ORDER.filter((c) => c !== "random" && perClass.some((r) => r.controller === c && r.regime === classRegime));
  const classGroups = classControllers.map((c) => ({
    label: controllerLabel(c).replace(/\s*\(.*\)$/, ""),
    bars: Object.keys(CLASS_LABEL)
      .map((k) => ({ k, row: perClass.find((r) => r.controller === c && r.regime === classRegime && r.class === k) }))
      .filter((x) => x.row)
      .map((x) => ({ key: CLASS_LABEL[x.k], value: x.row!.delay_mean, err: x.row!.delay_std, colour: CLASS_COLOURS[x.k] })),
  }));

  const co2Controllers = CONTROLLER_ORDER.filter((c) => c !== "random");
  const co2Groups = REGIMES.map((r) => ({
    label: REGIME_LABEL[r],
    bars: co2Controllers
      .map((c) => ({ c, row: mainValue(r, c, "co2") }))
      .filter((x) => x.row)
      .map((x, i) => ({
        key: controllerLabel(x.c), value: x.row!.mean, err: x.row!.std,
        colour: OURS.has(x.c) ? "var(--wave-b)" : `color-mix(in srgb, var(--muted) ${90 - i * 12}%, var(--surface-2))`,
      })),
  }));

  const groups = [...new Set(ablations.map((a) => a.group))];
  const ablationMetrics = ["person_wait", "max_wait", "delay_bus"];

  return (
    <>
      <PageHeader eyebrow="Results" title="Every controller, every regime"
        lead={`Each controller ran on ${meta.seeds.eval ?? 10} held-out traffic seeds per regime. RL rows average ${meta.seeds.train ?? 1} independently trained policies. Nothing on this page is typed by hand: it is all read from the evaluation files.`} />

      <Section className="!pt-8">
        <ResultsTable rows={main} regimes={[...REGIMES]} metrics={[...TABLE_METRICS]} metricInfo={METRICS}
          controllers={CONTROLLER_ORDER} labels={meta.controllers} ours={[...OURS]} reference="fixed_matched" />
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Learning curves" title="Double DQN, DQN and PPO on the same reward"
          lead="Validation score on two held-out seeds every 10k decisions, peak regime. Bands show one standard deviation across training seeds. The score is the time-averaged form of the training objective; higher is better." />
        <Card><CurveChart curves={curves} labels={meta.controllers} /></Card>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Generalisation" title="Train on one regime, test on all four"
          lead="Rows are the regime a policy was trained on, columns the regime it was tested on. Colours diverge around the diagonal mean: red cells are worse than regime-matched training. The last row is one policy trained with randomised demand." />
        <div className="grid gap-4 lg:grid-cols-2">
          {generalisation.map((g) => (
            <Card key={g.metric}>
              <h3 className="mb-3 text-sm font-medium">{METRICS[g.metric]?.label ?? g.metric} ({METRICS[g.metric]?.unit ?? ""})</h3>
              <Heatmap data={g} unit={METRICS[g.metric]?.unit ?? ""} />
              <p className="mt-3 text-sm text-muted">
                Gap recovered by domain randomisation:{" "}
                <span className="num font-semibold text-text">
                  {g.gap_recovered_pct === null ? "not defined (no gap)" : `${fmt(g.gap_recovered_pct, 0)}%`}
                </span>
              </p>
            </Card>
          ))}
        </div>
        <div className="mt-4 max-w-2xl"><FormulaBlock tex={TEX.gap} label="Gap recovered: off-diagonal mean minus DR, over off-diagonal mean minus diagonal mean" /></div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Fairness" title="Who waits longest under each reward design"
          lead="Cumulative distribution of per-vehicle waiting time in the skewed regime, where one approach carries most of the traffic. A long right tail means some vehicles were left waiting." />
        <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
          <Card><EcdfChart fairness={fairness} T={meta.reward.T ?? 90} /></Card>
          <div className="card overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Median, 95th percentile and maximum wait per reward design</caption>
              <thead><tr className="border-b border-line text-xs uppercase tracking-wider text-muted">
                <th scope="col" className="px-4 py-3 font-medium">Reward design</th>
                <th scope="col" className="px-3 py-3 text-right font-medium">p50</th>
                <th scope="col" className="px-3 py-3 text-right font-medium">p95</th>
                <th scope="col" className="px-3 py-3 text-right font-medium">max</th>
              </tr></thead>
              <tbody>
                {Object.entries(fairness).map(([k, f]) => (
                  <tr key={k} className="border-b border-line/60 last:border-0">
                    <th scope="row" className="px-4 py-2.5 font-medium">{f.label}</th>
                    <td className="num whitespace-nowrap px-3 py-2.5 text-right">{fmt(f.p50, 0)} s</td>
                    <td className="num whitespace-nowrap px-3 py-2.5 text-right">{fmt(f.p95, 0)} s</td>
                    <td className="num whitespace-nowrap px-3 py-2.5 text-right">{fmt(f.max, 0)} s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="By vehicle class" title="Delay per class, peak regime"
          lead="Mean time loss per vehicle. Passenger weighting should show up as lower bus delay." />
        <Card>
          <BarChart groups={classGroups} yLabel="delay (s)" ariaLabel="Mean delay per vehicle class for each controller in the peak regime"
            legend={Object.keys(CLASS_LABEL).map((k) => ({ label: CLASS_LABEL[k], colour: CLASS_COLOURS[k] }))} />
        </Card>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Ablations" title="What each design choice buys"
          lead="Each variant is trained with the ablation budget and compared with a reference trained with the same budget. Takeaways are produced from the numbers by fixed templates." />
        <div className="grid gap-4 lg:grid-cols-2">
          {groups.map((g) => {
            const rows = ablations.filter((a) => a.group === g);
            const variants = [...new Set(rows.map((r) => r.variant))];
            return (
              <Card key={g}>
                <h3 className="font-semibold">{ABLATION_TITLES[g] ?? g}</h3>
                <p className="mb-3 mt-1 text-xs text-muted">Regime: {REGIME_LABEL[rows[0]?.regime] ?? rows[0]?.regime}</p>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[360px] text-left text-sm">
                    <thead><tr className="border-b border-line text-xs uppercase tracking-wider text-muted">
                      <th scope="col" className="py-2 pr-3 font-medium">Variant</th>
                      {ablationMetrics.map((m) => (
                        <th key={m} scope="col" className="px-2 py-2 text-right font-medium">{METRICS[m]?.label ?? m}</th>
                      ))}
                    </tr></thead>
                    <tbody>
                      {variants.map((v) => (
                        <tr key={v} className="border-b border-line/60 last:border-0">
                          <th scope="row" className="py-2 pr-3 font-medium">
                            {v}{rows.find((r) => r.variant === v)?.reference ? <span className="ml-1.5 text-xs font-normal text-muted">(reference)</span> : null}
                          </th>
                          {ablationMetrics.map((m) => {
                            const r = rows.find((x) => x.variant === v && x.metric === m);
                            return <td key={m} className="num whitespace-nowrap px-2 py-2 text-right">
                              {r ? <>{fmt(r.mean, 1)}<span className="text-muted"> ± {fmt(r.std, 1)}</span></> : "–"}
                            </td>;
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-muted">{rows.find((r) => r.takeaway)?.takeaway}</p>
              </Card>
            );
          })}
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Emissions" title="CO2 per vehicle"
          lead="From SUMO's emissions device with default HBEFA classes per vehicle type. Less idling means less CO2, so this mostly tracks waiting time." />
        <Card>
          <BarChart groups={co2Groups} yLabel="CO2 (g per vehicle)" ariaLabel="CO2 per vehicle for each controller in each regime"
            legend={co2Controllers.filter((c) => main.some((r) => r.controller === c && r.metric === "co2")).map((c, i) => ({
              label: controllerLabel(c),
              colour: OURS.has(c) ? "var(--wave-b)" : `color-mix(in srgb, var(--muted) ${90 - i * 12}%, var(--surface-2))`,
            }))} />
        </Card>
      </Section>

      <Section className="border-t border-line">
        <Callout title="Deviations from the full protocol" tone="amber">
          <p className="text-base">
            Compute profile: <span className="num font-semibold">{meta.profile}</span>. Training seeds per configuration:{" "}
            <span className="num">{meta.seeds.train}</span>; evaluation seeds: <span className="num">{meta.seeds.eval}</span>.
            {meta.synthetic_demand ? " Demand is synthetic, not counted at a real junction." : ""}
          </p>
          {meta.deviations.length ? (
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted">
              {meta.deviations.map((d) => <li key={d}>{d}</li>)}
            </ul>
          ) : <p className="text-sm text-muted">No deviations recorded.</p>}
        </Callout>
      </Section>
    </>
  );
}
