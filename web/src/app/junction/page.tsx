import { existsSync } from "node:fs";
import { join } from "node:path";
import type { Metadata } from "next";
import { NetworkFigure } from "@/components/NetworkFigure";
import { Callout, Card, DataTable, PageHeader, Section, SectionHeading } from "@/components/ui";
import { demand, meta, network } from "@/lib/data";
import { fmt } from "@/lib/format";
import { CLASS_LABEL, REGIMES, REGIME_LABEL } from "@/lib/types";

export const metadata: Metadata = {
  title: "The junction",
  description: "Geometry, signal phasing and demand of the simulated junction, with every modelling assumption stated.",
  alternates: { canonical: "/junction/" },
};

const REGIME_NOTE: Record<string, string> = {
  low: "0.4 × peak on every approach",
  peak: "1.0 × peak",
  skewed: "east approach 1.6 × peak, the others 0.6 ×",
  surge: "0.7 × peak, plus a 10-minute burst at 2.5 × on the east approach",
};

export default function JunctionPage() {
  const f = network.facts as { lanes_in: Record<string, number>; lanes_out: Record<string, number> } & Record<string, unknown>;
  const hasPhoto = existsSync(join(process.cwd(), "public", "site.jpg"));
  return (
    <>
      <PageHeader eyebrow="Junction" title="The junction being controlled" lead={`${meta.junction_name}. Left-hand traffic, four approaches, one signal.`} />

      <Section className="!pt-8">
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="flex min-h-64 flex-col">
            <h2 className="mb-3 text-sm font-medium text-muted">Site photo</h2>
            {hasPhoto ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src="/site.jpg" alt="Photograph of the real junction" className="w-full flex-1 rounded-[10px] object-cover" />
            ) : (
              <div className="grid flex-1 place-items-center rounded-[10px] border border-dashed border-line p-6 text-center">
                <div>
                  <p className="font-medium">Site photo not added</p>
                  <p className="mt-2 max-w-xs text-sm leading-relaxed text-muted">
                    This build models a generic four-arm junction from lane counts, not a named site. Drop a photo at{" "}
                    <code className="num">web/public/site.jpg</code> to show it here.
                  </p>
                </div>
              </div>
            )}
          </Card>
          <Card>
            <h2 className="mb-3 text-sm font-medium text-muted">Simulated network (plan view, north up)</h2>
            <NetworkFigure network={network} />
          </Card>
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Geometry and signals" title="Network facts" />
        <div className="grid gap-4 lg:grid-cols-2">
          <DataTable caption="Lanes per approach" head={["Approach", "Lanes in", "Lanes out", "Role"]}
            rows={network.approaches.map((a) => [a, String(f.lanes_in[a]), String(f.lanes_out[a]), <span key={a} className="font-sans">{f.lanes_in[a] >= 3 ? "major road" : "minor road"}</span>])} />
          <DataTable caption="Signal facts" head={["Property", "Value"]}
            rows={[
              ["Source of geometry", <span key="1" className="font-sans">{meta.network_source === "osm" ? "OpenStreetMap import" : "plain XML, simplified by hand to lane counts"}</span>],
              ["Phases", <span key="1" className="font-sans">{String(f.phases)}, one per approach (split phasing), each serving all movements of its approach</span>],
              ["Free left turn", <span key="1" className="font-sans">{f.free_left ? "yes: left-turners may go on red after yielding" : "no"}</span>],
              ["Approach length", `${String(f.approach_length_m)} m`],
              ["Lane width", `${String(f.lane_width_m)} m`],
              ["Green limits", `${String(f.min_green)} – ${String(f.max_green)} s`],
              ["Yellow", `${String(f.yellow)} s`],
              ["Simulator", `SUMO ${meta.sumo_version}, sub-lane model`],
            ]} />
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Demand" title="Four demand regimes"
          lead="Vehicles per hour entering the junction, time-averaged over the episode." />
        {meta.synthetic_demand ? (
          <div className="mb-4">
            <Callout title="Synthetic demand" tone="amber">
              <p className="text-base">
                No vehicles were counted at a real junction for this build. Volumes are generated from an assumed class
                mix and turn split, scaled so the peak Webster plan runs at a degree of saturation of about 0.85.
              </p>
            </Callout>
          </div>
        ) : null}
        <DataTable caption="Demand per regime and vehicle class"
          head={["Regime", ...demand.classes.map((c) => CLASS_LABEL[c] ?? c), "Total veh/h", "Webster cycle"]}
          rows={REGIMES.filter((r) => demand.regimes[r]).map((r) => {
            const d = demand.regimes[r];
            const total = Object.values(d.veh_per_hour_by_class).reduce((s, v) => s + v, 0);
            return [
              <span key={r}><span className="font-sans font-medium">{REGIME_LABEL[r]}</span><span className="block font-sans text-xs font-normal text-muted">{REGIME_NOTE[r]}</span></span>,
              ...demand.classes.map((c) => fmt(d.veh_per_hour_by_class[c], 0)),
              fmt(total, 0),
              `${fmt(d.webster.cycle, 0)} s`,
            ];
          })} />
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <DataTable caption="Demand per regime and approach, in PCU per hour" head={["Regime", ...network.approaches.map((a) => `${a} (PCU/h)`)]}
            rows={REGIMES.filter((r) => demand.regimes[r]).map((r) => [REGIME_LABEL[r], ...network.approaches.map((a) => fmt(demand.regimes[r].pcu_per_hour[a], 0))])} />
          <DataTable caption="PCU factors and passenger weights" head={["Class", "Share", "PCU", "Passengers"]}
            rows={demand.classes.map((c) => [CLASS_LABEL[c] ?? c, `${fmt(demand.class_mix[c] * 100, 0)}%`, fmt(demand.pcu[c], 1), fmt(demand.passenger_weights[c], 1)])} />
        </div>
        <p className="mt-3 max-w-3xl text-xs leading-relaxed text-muted">
          Turn split on every approach: 25% left, 55% through, 20% right. PCU factors are IRC:106-1990 style
          assumptions; passenger weights are assumed average occupancies.
        </p>
      </Section>
    </>
  );
}
