import type { Metadata } from "next";
import { Card, DataTable, FormulaBlock, InlineMath, PageHeader, Section, SectionHeading } from "@/components/ui";
import { demand, meta, network } from "@/lib/data";
import { fmt } from "@/lib/format";
import { TEX } from "@/lib/formulas";
import { CLASS_LABEL } from "@/lib/types";

export const metadata: Metadata = {
  title: "Method",
  description: "The decision process, reward design, agents, baselines and evaluation protocol behind GreenWave-RL.",
  alternates: { canonical: "/method/" },
};

function StateMachine() {
  const box = "fill-[var(--surface-2)] stroke-[var(--line)]";
  return (
    <svg viewBox="0 0 720 230" className="w-full" role="img"
      aria-label="Timing state machine: a green phase is either extended by five seconds or passes through three seconds of yellow to a new green held for at least ten seconds">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="var(--muted)" />
        </marker>
      </defs>
      <g fontSize="13" fill="var(--text)" textAnchor="middle" className="num">
        <rect x="40" y="80" width="150" height="64" rx="12" className={box} />
        <circle cx="62" cy="112" r="6" fill="var(--go)" />
        <text x="122" y="108">GREEN(p)</text>
        <text x="122" y="126" fontSize="11" fill="var(--muted)">10 – 60 s</text>

        <rect x="290" y="80" width="140" height="64" rx="12" className={box} />
        <circle cx="312" cy="112" r="6" fill="var(--amber)" />
        <text x="368" y="108">YELLOW(p)</text>
        <text x="368" y="126" fontSize="11" fill="var(--muted)">3 s, always</text>

        <rect x="530" y="80" width="150" height="64" rx="12" className={box} />
        <circle cx="552" cy="112" r="6" fill="var(--go)" />
        <text x="612" y="108">GREEN(q)</text>
        <text x="612" y="126" fontSize="11" fill="var(--muted)">min 10 s, no query</text>

        <path d="M190 112H286" stroke="var(--muted)" fill="none" markerEnd="url(#arrow)" />
        <text x="238" y="102" fontSize="11" fill="var(--muted)">picks q ≠ p</text>
        <path d="M430 112H526" stroke="var(--muted)" fill="none" markerEnd="url(#arrow)" />
        <text x="478" y="102" fontSize="11" fill="var(--muted)">[all-red]</text>
        <path d="M90 80C90 28 160 28 160 76" stroke="var(--muted)" fill="none" markerEnd="url(#arrow)" />
        <text x="125" y="26" fontSize="11" fill="var(--muted)">picks p: +5 s</text>
        <path d="M122 144C122 208 612 208 612 148" stroke="var(--stop)" strokeDasharray="5 4" fill="none" markerEnd="url(#arrow)" />
        <text x="368" y="218" fontSize="11" fill="var(--stop)">at 60 s: forced switch to the longest-waiting approach (via yellow)</text>
      </g>
    </svg>
  );
}

export default function MethodPage() {
  const f = network.facts as Record<string, number | boolean | string>;
  const r = meta.reward;
  return (
    <>
      <PageHeader eyebrow="Method" title="How the controller is framed, trained and tested"
        lead="Given a signalised junction with time-varying, mixed traffic: learn a phase-selection policy that minimises delay per person, keeps the worst-case wait bounded, and stays effective when demand shifts away from what it was trained on." />

      <Section className="!pt-8">
        <SectionHeading eyebrow="1 · Decision process" title="The Markov decision process" />
        <DataTable caption="Elements of the decision process" head={["Element", "Definition"]}
          rows={[
            ["State", <span key="s" className="font-sans">Per incoming lane: PCU-weighted halting queue and PCU density, each divided by lane capacity. Plus the current green approach (one-hot), time since the last change over maximum green, and the longest accumulated wait on each approach over T. 29 numbers at this junction.</span>],
            ["Action", <span key="a" className="font-sans">The approach to serve next. Choosing the current one extends its green by {String(f.decision_interval)} s.</span>],
            ["Safety constraints", <span key="c" className="font-sans">Minimum green {String(f.min_green)} s, yellow {String(f.yellow)} s on every change, maximum green {String(f.max_green)} s. Enforced by the environment, never learned.</span>],
            ["Reward", <span key="r" className="font-sans">Passenger-weighted reduction in accumulated waiting time, minus a penalty when any approach waits longer than T.</span>],
            ["Episode", <span key="e" className="font-sans">3,600 simulated seconds, discount 0.99 per decision. The end is a truncation, not a termination: the value of the last state is bootstrapped.</span>],
          ]} />
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
          The state is not strictly Markov: it omits upstream arrivals and vehicles between observations, so the
          agent works under partial observability. Transitions last 5 s when a green is extended and 13 s when it
          changes (3 s yellow plus 10 s minimum green); a constant discount per decision is used, a semi-MDP
          simplification.
        </p>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="2 · Safety" title="The timing state machine"
          lead="The agent is only asked for a decision at legal decision points. A learned penalty can be traded away; a constraint in the environment cannot." />
        <Card><StateMachine /></Card>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="3 · Reward" title="Counting people, bounding the worst wait" />
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <p className="mb-2 text-sm font-medium">Baseline: waiting-time reduction</p>
            <FormulaBlock tex={TEX.rewardWait} label="Baseline reward: reduction in total accumulated waiting time, divided by kappa" />
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">Ours: passenger-weighted with a fairness penalty</p>
            <FormulaBlock tex={TEX.rewardOurs} label="Our reward: passenger-weighted waiting-time reduction minus a fairness penalty" />
          </div>
        </div>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
          <InlineMath tex="W_{c,t}" /> is the summed accumulated waiting time of class-<InlineMath tex="c" /> vehicles
          on the incoming lanes, <InlineMath tex="w_c" /> the passenger weight of the class, and{" "}
          <InlineMath tex="\text{wait}_a" /> the longest accumulated wait on approach <InlineMath tex="a" />. Values used:{" "}
          <InlineMath tex={`\\kappa = ${fmt(r.kappa ?? 100, 0)}`} />, <InlineMath tex={`\\lambda = ${fmt(r.lambda ?? 1, 2)}`} />,{" "}
          <InlineMath tex={`T = ${fmt(r.T ?? 90, 0)}\\,\\text{s}`} /> (λ and T chosen by a nine-run sweep on the skewed
          regime). In the reward the passenger weights are divided by the mean occupancy of the traffic mix, which keeps
          their ratios and puts the reward on the same scale as the vehicle-count version.
        </p>
        <div className="mt-6">
          <DataTable caption="Assumed PCU factors and passenger weights per vehicle class"
            head={["Vehicle class", "Share of traffic", "PCU factor", "Passenger weight"]}
            rows={demand.classes.map((c) => [CLASS_LABEL[c] ?? c, `${fmt(demand.class_mix[c] * 100, 0)}%`, fmt(demand.pcu[c], 1), fmt(demand.passenger_weights[c], 1)])} />
          <p className="mt-2 text-xs text-muted">
            PCU factors follow IRC:106-1990 style values; passenger weights are stated occupancy assumptions. The bus
            weight is tested at 20, 40 and 60 in the ablations.
          </p>
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="4 · Agents" title="Double DQN from scratch, two library agents for comparison" />
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <p className="mb-2 text-sm font-medium">DQN loss</p>
            <FormulaBlock tex={TEX.dqnLoss} label="DQN loss: squared temporal-difference error against a target network" />
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">Double DQN target (the scratch agent)</p>
            <FormulaBlock tex={TEX.ddqnTarget} label="Double DQN target: the online network selects the action, the target network evaluates it" />
          </div>
        </div>
        <div className="mt-6">
          <DataTable caption="Agents" head={["Agent", "Implementation", "Key settings"]}
            rows={[
              ["Double DQN (main)", <span key="1" className="font-sans">Written from scratch in PyTorch</span>, <span key="2" className="font-sans">MLP 128-128, replay 50k, batch 64, Adam 1e-4, target sync every 500 steps, ε 1.0 → 0.05 over half of training, Huber loss, gradient clip 10</span>],
              ["DQN", <span key="1" className="font-sans">Stable-Baselines3 (vanilla DQN, not Double)</span>, <span key="2" className="font-sans">Same network, buffer, learning rate and exploration schedule</span>],
              ["PPO", <span key="1" className="font-sans">Stable-Baselines3</span>, <span key="2" className="font-sans">4 parallel simulations, 512 steps per rollout, 10 epochs, clip 0.2, entropy 0.01</span>],
            ]} />
        </div>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
          In the target, <InlineMath tex="d = 1" /> only on true termination. Episodes end by time limit, so{" "}
          <InlineMath tex="d" /> is always 0 here and the agent bootstraps from the final state. Checkpoints are chosen
          on two validation seeds that are used neither for training nor for evaluation.
        </p>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="5 · Baselines" title="What the agent has to beat"
          lead="All baselines run through the same environment and are scored by the same code." />
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <h3 className="font-semibold">Fixed-time (Webster)</h3>
            <p className="mb-3 mt-2 text-sm leading-relaxed text-muted">
              Cycle length from Webster&apos;s formula with lost time L, green split in proportion to each approach&apos;s
              flow ratio. Two variants: a plan computed for each regime (the strongest fixed-time) and the peak plan
              applied everywhere (the realistic stale plan).
            </p>
            <FormulaBlock tex={TEX.webster} label="Webster optimal cycle length" />
          </Card>
          <Card>
            <h3 className="font-semibold">Max-pressure</h3>
            <p className="mb-3 mt-2 text-sm leading-relaxed text-muted">
              At every decision point, serve the phase with the largest pressure: queued PCU on its incoming lanes
              minus queued PCU on the lanes they feed. Throughput-optimal under idealised assumptions and needs no
              training, which makes it the baseline to take seriously.
            </p>
            <FormulaBlock tex={TEX.pressure} label="Pressure of a phase: sum over its movements of incoming minus outgoing queue" />
          </Card>
          <Card>
            <h3 className="font-semibold">Actuated</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              SUMO&apos;s built-in gap-based controller: a green is extended while vehicles keep arriving within 3 s
              of each other, between 10 s and 60 s.
            </p>
          </Card>
          <Card>
            <h3 className="font-semibold">Random phase</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              A uniformly random approach at every decision, under the same timing constraints. The sanity floor.
            </p>
          </Card>
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="6 · Protocol" title="Training and evaluation" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <h3 className="font-semibold">Training pipeline</h3>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-muted">
              <li>Measure simulation speed and pick the largest compute profile that fits the time budget.</li>
              <li>Sweep λ and T on the skewed regime; keep the setting with the lowest person delay subject to a bound on the maximum wait.</li>
              <li>Train Double DQN on each of the four regimes and on randomised demand, {meta.seeds.train} seeds each.</li>
              <li>Train DQN and PPO on the peak regime with the same reward.</li>
              <li>Train one ablation at a time against a budget-matched reference.</li>
            </ol>
          </Card>
          <Card>
            <h3 className="font-semibold">Evaluation protocol</h3>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-muted">
              <li>Freeze the policy: ε = 0, deterministic actions.</li>
              <li>Run {meta.seeds.eval} evaluation seeds per regime per controller; the seeds are never used in training.</li>
              <li>Export a trip record for every vehicle, plus per-second queues and signal states.</li>
              <li>Report mean ± standard deviation over seeds and Welch&apos;s t-test against fixed-time and max-pressure.</li>
            </ol>
          </Card>
        </div>
        <div className="mt-6">
          <DataTable caption="Metric definitions" head={["Metric", "Definition"]}
            rows={[
              ["Wait per vehicle", <span key="1" className="font-sans">Mean time spent below 0.1 m/s, over all vehicles including unfinished trips</span>],
              ["Wait per person", <span key="1" className="font-sans">The same, weighted by the passenger weight of each vehicle&apos;s class</span>],
              ["Max wait", <span key="1" className="font-sans">Largest per-vehicle wait on each approach; the maximum over approaches is reported</span>],
              ["Wait p95", <span key="1" className="font-sans">95th percentile of per-vehicle wait</span>],
              ["Avg queue", <span key="1" className="font-sans">Halting vehicles on the incoming lanes, averaged over every second</span>],
              ["Throughput", <span key="1" className="font-sans">Vehicles that completed their trip per simulated hour</span>],
              ["CO2", <span key="1" className="font-sans">Mean CO2 per vehicle from SUMO&apos;s emissions device</span>],
            ]} />
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="7 · Data" title="Where the traffic comes from" />
        <Card>
          <p className="max-w-3xl text-sm leading-relaxed text-muted">
            {meta.synthetic_demand
              ? "Demand in this build is synthetic: no vehicles were counted at a real junction. "
              : "Demand is scaled from field counts. "}
            Peak volume is chosen so that the Webster plan sits at a degree of saturation of about 0.85, with the major
            road carrying 1.5 times the minor road. Arrivals are Poisson per origin, destination and class. Training
            samples a fresh simulation seed every episode; with domain randomisation each approach&apos;s flow is also
            scaled by an independent factor between 0.5 and 1.5.
          </p>
        </Card>
      </Section>
    </>
  );
}
