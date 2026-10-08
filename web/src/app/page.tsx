import Link from "next/link";
import { BarChart, Heatmap } from "@/components/charts";
import { HeroCanvas } from "@/components/HeroCanvas";
import { PipelineDiagram } from "@/components/PipelineDiagram";
import { Counter, Reveal } from "@/components/Reveal";
import { Callout, Card, FormulaBlock, Section, SectionHeading } from "@/components/ui";
import { CONTROLLER_ORDER, OURS, controllerLabel, generalisation, mainValue, meta, network } from "@/lib/data";
import { TEX } from "@/lib/formulas";
import { REGIME_LABEL } from "@/lib/types";

const PROBLEMS = [
  {
    title: "Plans go stale",
    text: "Signal timing is tuned by hand for an average hour. Demand changes by the minute.",
    icon: <path d="M12 6v6l4 2M12 3a9 9 0 1 0 9 9" />,
  },
  {
    title: "Traffic is mixed",
    text: "Two-wheelers, autos, cars and buses share lanes loosely. Most published RL signal work assumes neat car queues.",
    icon: <path d="M3 15h4l2-5h6l2 5h4M7 18a1.5 1.5 0 1 0 0-.01M17 18a1.5 1.5 0 1 0 0-.01" />,
  },
  {
    title: "A bus is not a car",
    text: "Counting vehicles equally undervalues a bus carrying forty people against a car carrying two.",
    icon: <path d="M5 16V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v9M5 11h14M4 16h16M8 19v-3M16 19v-3" />,
  },
  {
    title: "Averages can starve",
    text: "An agent that minimises average delay can learn to hold a minor road on red. A deployable controller must not.",
    icon: <path d="M12 4v8M12 16v.01M4.5 19h15L12 5z" />,
  },
];

function KpiTile({ label, value, detail }: { label: string; value: number | null; detail: string }) {
  const good = value !== null && value < 0;
  return (
    <div className="card card-focus bg-surface-1/80 p-4 backdrop-blur sm:p-5">
      <p className={`text-3xl font-semibold sm:text-4xl ${value === null ? "text-muted" : good ? "text-go" : "text-stop"}`}>
        {value === null ? (
          <span className="num text-2xl">pending</span>
        ) : (
          <Counter value={value} prefix={value < 0 ? "−" : "+"} suffix="%" />
        )}
      </p>
      <p className="mt-2 text-sm font-medium">{label}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{detail}</p>
    </div>
  );
}

export default function HomePage() {
  const regime = meta.headline.regime;
  const bars = CONTROLLER_ORDER.filter((c) => c !== "random")
    .map((c) => ({ c, row: mainValue(regime, c, "person_wait") }))
    .filter((x) => x.row)
    .map((x) => ({
      label: controllerLabel(x.c).replace(/\s*\(.*\)$/, ""),
      bars: [{ key: controllerLabel(x.c), value: x.row!.mean, err: x.row!.std, colour: OURS.has(x.c) ? "var(--wave-b)" : "var(--muted)" }],
    }));
  const person = generalisation.find((g) => g.metric === "person_wait");

  return (
    <>
      {/* 1. Hero */}
      <section className="relative isolate overflow-hidden border-b border-line">
        <HeroCanvas network={network} />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(90deg, rgba(var(--scrim),0.96) 0%, rgba(var(--scrim),0.82) 45%, rgba(var(--scrim),0.35) 100%), linear-gradient(0deg, rgba(var(--scrim),0.9) 0%, rgba(var(--scrim),0) 45%)",
          }}
        />
        <div className="relative mx-auto max-w-6xl px-4 pb-12 pt-20 sm:px-6 sm:pb-16 sm:pt-28">
          <p className="num mb-5 text-xs uppercase tracking-[0.18em] text-muted">
            Deep RL · adaptive signal control · mixed Indian traffic
          </p>
          <h1 className="display max-w-4xl font-semibold">
            Signal timing, <em className="wave-text pr-2 font-serif font-normal italic">learned</em>.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted sm:text-xl">
            Fixed-time signals cannot respond to demand that changes by the minute. GreenWave trains agents to choose
            signal phases from live queues, weighting people rather than vehicles and never starving a minor road.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/demo/"
              className="rounded-full bg-gradient-to-r from-wave-a to-wave-b px-5 py-2.5 text-sm font-semibold text-[#04130b]"
            >
              Watch the duel
            </Link>
            <Link href="/method/" className="rounded-full border border-line bg-surface-1/70 px-5 py-2.5 text-sm font-semibold backdrop-blur hover:border-wave-b">
              Read the method
            </Link>
          </div>
          <div className="mt-12 grid gap-3 sm:grid-cols-3">
            {meta.kpis.map((k) => (
              <KpiTile key={k.key} label={k.label} value={k.value} detail={k.detail} />
            ))}
          </div>
        </div>
      </section>

      {/* 2. The problem */}
      <Section>
        <Reveal>
          <SectionHeading eyebrow="The problem" title="Four reasons a timer is not enough" />
        </Reveal>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PROBLEMS.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.05}>
              <Card className="card-focus h-full">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--wave-b)" strokeWidth="1.5"
                  strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  {p.icon}
                </svg>
                <h3 className="mt-4 font-semibold">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{p.text}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* 3. How it works */}
      <Section className="border-t border-line">
        <Reveal>
          <SectionHeading eyebrow="How it works" title="From lane counts to a learned policy"
            lead="Eight stages, one command each. Hover or tab through them." />
          <PipelineDiagram />
        </Reveal>
      </Section>

      {/* 4. Three contributions */}
      <Section className="border-t border-line">
        <Reveal>
          <SectionHeading eyebrow="What is new here" title="Three choices that separate this from a tutorial"
            lead="Reinforcement learning for traffic signals is a well-published field. The contribution is in these three choices, not the idea." />
        </Reveal>
        <div className="grid gap-4 lg:grid-cols-3">
          <Reveal className="lg:col-span-3">
            <Card>
              <h3 className="font-semibold">1 · A passenger-weighted, fairness-aware reward</h3>
              <p className="mb-4 mt-2 max-w-3xl text-sm leading-relaxed text-muted">
                Waiting time is weighted by how many people each vehicle class carries, and a penalty switches on
                when the longest wait on any approach exceeds a threshold T.
              </p>
              <FormulaBlock tex={TEX.rewardOurs} label="Reward: passenger-weighted waiting-time reduction minus a fairness penalty" />
            </Card>
          </Reveal>
          <Reveal>
            <Card className="h-full">
              <h3 className="font-semibold">2 · A mixed-traffic setting</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                Left-hand traffic, four vehicle classes with sub-lane movement, free left turns and approach-wise split
                phasing as used at Indian junctions. Not a synthetic grid of identical cars.
              </p>
            </Card>
          </Reveal>
          <Reveal delay={0.05} className="lg:col-span-2">
            <Card className="h-full">
              <h3 className="font-semibold">3 · An honest generalisation study</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                Train on one demand regime, test on the others, report the failures, and measure how much of the loss
                domain randomisation recovers. Max-pressure, a rule that needs no training, is kept in every table.
              </p>
            </Card>
          </Reveal>
        </div>
      </Section>

      {/* 5. Results at a glance */}
      <Section className="border-t border-line">
        <Reveal>
          <SectionHeading eyebrow="Results at a glance" title={`Waiting time per person, ${REGIME_LABEL[regime] ?? regime} regime`}
            lead={<>Mean of ten held-out seeds; whiskers show one standard deviation. <Link href="/results/" className="text-text underline decoration-line underline-offset-4 hover:decoration-wave-b">All regimes and metrics</Link>.</>} />
        </Reveal>
        <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
          <Reveal>
            <Card className="h-full">
              <BarChart groups={bars} yLabel="wait per person (s)" digits={0}
                ariaLabel={`Waiting time per person for each controller in the ${regime} regime`}
                legend={[{ label: "Baselines", colour: "var(--muted)" }, { label: "GreenWave (ours)", colour: "var(--wave-b)" }]} />
            </Card>
          </Reveal>
          <Reveal delay={0.05}>
            <Card className="h-full">
              <h3 className="mb-1 text-sm font-medium">Generalisation: trained on (rows) × tested on (columns)</h3>
              <p className="mb-3 text-xs text-muted">Wait per person in seconds. Red is worse than regime-matched training.</p>
              {person ? <Heatmap data={person} unit="s" compact /> : <p className="text-sm text-muted">Pending.</p>}
              {person?.gap_recovered_pct != null ? (
                <p className="mt-3 text-sm text-muted">
                  Domain randomisation recovers{" "}
                  <span className="num font-semibold text-text">{person.gap_recovered_pct.toFixed(0)}%</span> of the
                  generalisation gap.
                </p>
              ) : null}
            </Card>
          </Reveal>
        </div>
      </Section>

      {/* 6. The honest finding */}
      <Section className="border-t border-line">
        <Reveal>
          <Callout title="The honest finding">
            <p>{meta.honest_finding || "Pending: this paragraph is generated from the evaluation data."}</p>
            <p className="text-sm text-muted">
              Generated from the result files by fixed templates. See the{" "}
              <Link href="/demo/" className="underline decoration-line underline-offset-4 hover:decoration-wave-b">Honest scene</Link>{" "}
              and the <Link href="/results/" className="underline decoration-line underline-offset-4 hover:decoration-wave-b">full tables</Link>.
            </p>
          </Callout>
        </Reveal>
      </Section>
    </>
  );
}
