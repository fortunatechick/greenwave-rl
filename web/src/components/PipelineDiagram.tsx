"use client";

import { useState } from "react";

const STAGES = [
  { id: "network", name: "Network builder", text: "Turns lane counts into a left-hand SUMO junction with approach-wise split phasing." },
  { id: "demand", name: "Demand generator", text: "Poisson arrivals for four vehicle classes across low, peak, skewed and surge regimes." },
  { id: "sumo", name: "SUMO", text: "Microscopic simulation with the sub-lane model, so two-wheelers filter between cars." },
  { id: "env", name: "Gym environment", text: "Wraps SUMO as an MDP and enforces minimum green, yellow and maximum green itself." },
  { id: "agent", name: "Agent", text: "Double DQN written from scratch, plus Stable-Baselines3 DQN and PPO for comparison." },
  { id: "baselines", name: "Baselines", text: "Webster fixed-time, actuated, max-pressure and random, through the same environment." },
  { id: "evaluator", name: "Evaluator", text: "Ten held-out seeds per regime, per-vehicle trip records, Welch t-tests." },
  { id: "demo", name: "Demo", text: "Recorded simulations replayed here, and a live side-by-side in SUMO GUI." },
];

/** The eight system stages. Hover or focus a stage for a one-line description. */
export function PipelineDiagram() {
  const [active, setActive] = useState(0);
  return (
    <div>
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        {STAGES.map((s, i) => (
          <li key={s.id} className="relative">
            <button
              type="button"
              onMouseEnter={() => setActive(i)}
              onFocus={() => setActive(i)}
              aria-pressed={active === i}
              aria-describedby="pipeline-detail"
              className={`card card-focus flex h-full w-full flex-col items-start gap-2 p-3 text-left transition-colors ${
                active === i ? "border-wave-b/70" : ""
              }`}
            >
              <span className="num text-xs text-muted">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-sm font-medium leading-tight">{s.name}</span>
            </button>
            {i < STAGES.length - 1 ? (
              <svg aria-hidden width="10" height="10" viewBox="0 0 10 10"
                className="absolute -right-[9px] top-1/2 z-10 hidden -translate-y-1/2 text-muted lg:block">
                <path d="M1 5h7M5 2l3 3-3 3" fill="none" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            ) : null}
          </li>
        ))}
      </ol>
      <p id="pipeline-detail" aria-live="polite" className="mt-4 min-h-[3rem] text-sm leading-relaxed text-muted sm:text-base">
        <span className="font-medium text-text">{STAGES[active].name}.</span> {STAGES[active].text}
      </p>
    </div>
  );
}
