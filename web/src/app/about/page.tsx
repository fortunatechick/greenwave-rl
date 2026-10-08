import type { Metadata } from "next";
import Link from "next/link";
import { Card, PageHeader, Section, SectionHeading } from "@/components/ui";
import { repoUrl } from "@/lib/data";

export const metadata: Metadata = {
  title: "About",
  description: "Credits, technology, limitations, future work and a short viva-style FAQ for GreenWave-RL.",
  alternates: { canonical: "/about/" },
};

const STACK = [
  ["Simulation", "SUMO with the sub-lane model, driven through libsumo and TraCI"],
  ["Environment", "Gymnasium, with safety constraints enforced in the environment"],
  ["Agents", "Double DQN in PyTorch (from scratch); DQN and PPO from Stable-Baselines3"],
  ["Analysis", "pandas, NumPy, SciPy (Welch t-tests), Matplotlib, seaborn"],
  ["Website", "Next.js static export, Tailwind CSS, Motion, Recharts, KaTeX, deployed on Vercel"],
];

const LIMITS = [
  ["Sim-to-real gap", "Nothing here has run on a street. Real deployment adds sensing errors, driver behaviour, pedestrians and safety certification."],
  ["Perfect observations", "The agent reads exact queues and waiting times from the simulator. A camera or loop detector would be noisier and partial."],
  ["Semi-MDP simplification", "Decisions last 5 s or 13 s but are discounted by a constant factor per decision."],
  ["One junction", "A single isolated junction has no downstream spill-back, which is where coordinated control matters most."],
  ["Synthetic demand", "Volumes follow stated assumptions, not field counts. Occupancy weights are assumptions too."],
];

const FUTURE = [
  "A corridor of three to five junctions with coordinated multi-agent control.",
  "Emergency-vehicle and bus priority as explicit objectives.",
  "Camera-based state estimation in place of perfect simulator observations.",
  "Pedestrian phases.",
];

const FAQ = [
  ["Is the state Markov?", "Not strictly. It omits upstream arrivals and what happens between observations, so the agent works under partial observability. It still works because queues and waits summarise most of what matters for the next few seconds."],
  ["Why a target network and a replay buffer?", "Q-learning with function approximation chases a target that moves with every update and learns from correlated samples. A frozen target network stabilises the target; replay breaks the correlation."],
  ["Why does DQN overestimate, and what does Double DQN change?", "Taking the maximum over noisy estimates is biased upward. Double DQN lets the online network choose the action and the target network score it, which removes most of that bias."],
  ["Why is the reward not simply negative waiting time?", "The difference form rewards the change the action caused, which is denser and bounded, and makes credit assignment easier than a large always-negative number."],
  ["Why can max-pressure match the agent?", "It is throughput-optimal under idealised assumptions and needs no training. On one isolated junction there is little for learning to add beyond it; the Results page reports where each one wins."],
  ["Why are safety constraints in the environment, not the reward?", "A constraint is a hard guarantee. A penalty is something the agent may decide is worth paying."],
  ["Why is the end of an episode a truncation?", "Traffic does not stop at 3,600 s. Treating the time limit as a terminal state would teach the agent that nothing after it matters and bias values near the end."],
];

const READING = [
  "Sutton and Barto, Reinforcement Learning: An Introduction",
  "Mnih et al. (2015), Human-Level Control through Deep Reinforcement Learning",
  "van Hasselt et al. (2016), Deep Reinforcement Learning with Double Q-Learning",
  "Schulman et al. (2017), Proximal Policy Optimization Algorithms",
  "Varaiya (2013), Max Pressure Control of a Network of Signalized Intersections",
  "Wei et al. (2018), IntelliLight; Wei et al. (2019), PressLight",
  "Wei et al. (2019), A Survey on Traffic Signal Control Methods",
  "Ault and Sharon (2021), Reinforcement Learning Benchmarks for Traffic Signal Control",
  "Lopez et al. (2018), Microscopic Traffic Simulation using SUMO",
  "IRC:106-1990 (PCU values); IRC:SP:41 (junction design)",
];

export default function AboutPage() {
  return (
    <>
      <PageHeader eyebrow="About" title="Credits, limits and what comes next"
        lead="GreenWave-RL is a course project for Artificial Intelligence, B.Tech Computer Engineering, 3rd year." />

      <Section className="!pt-8">
        <SectionHeading eyebrow="Built with" title="Technology" />
        <div className="card divide-y divide-line">
          {STACK.map(([k, v]) => (
            <div key={k} className="grid gap-1 px-5 py-3.5 sm:grid-cols-[10rem_1fr]">
              <p className="text-sm font-medium">{k}</p>
              <p className="text-sm text-muted">{v}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">
          Code, configs and trained checkpoints:{" "}
          <Link href={repoUrl} className="text-text underline decoration-line underline-offset-4 hover:decoration-wave-b">the GitHub repository</Link>.
          One command regenerates every number on this site.
        </p>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Honest limits" title="What this project does not show" />
        <div className="grid gap-4 sm:grid-cols-2">
          {LIMITS.map(([k, v]) => (
            <Card key={k}>
              <h3 className="font-semibold">{k}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{v}</p>
            </Card>
          ))}
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Next" title="Future extensions" />
        <ul className="grid gap-3 sm:grid-cols-2">
          {FUTURE.map((x) => (
            <li key={x} className="card px-5 py-4 text-sm leading-relaxed">{x}</li>
          ))}
        </ul>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Viva" title="Seven questions worth asking" />
        <div className="space-y-3">
          {FAQ.map(([q, a]) => (
            <details key={q} className="card group px-5 py-4">
              <summary className="cursor-pointer list-none font-medium marker:hidden">
                <span className="mr-2 inline-block text-muted transition-transform group-open:rotate-90" aria-hidden>›</span>
                {q}
              </summary>
              <p className="mt-3 pl-5 text-sm leading-relaxed text-muted">{a}</p>
            </details>
          ))}
        </div>
      </Section>

      <Section className="border-t border-line">
        <SectionHeading eyebrow="Sources" title="Reading list" />
        <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted">
          {READING.map((x) => <li key={x}>{x}</li>)}
        </ul>
        <p className="mt-3 text-xs text-muted">Listed from memory; titles, years and IRC values should be confirmed before citing.</p>
      </Section>
    </>
  );
}
