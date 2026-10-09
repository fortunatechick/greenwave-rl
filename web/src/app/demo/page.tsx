import type { Metadata } from "next";
import { Arena } from "@/components/replay/Arena";
import { PageHeader } from "@/components/ui";
import { corridor, meta, network } from "@/lib/data";

export const metadata: Metadata = {
  title: "The Arena",
  description: "Side-by-side replays of recorded SUMO simulations: fixed-time, max-pressure and learned signal control on identical traffic.",
  alternates: { canonical: "/demo/" },
};

const SCENES = [
  { id: "hero", label: "Hero" },
  { id: "surge", label: "Surge" },
  { id: "starvation", label: "Starvation" },
  { id: "bus", label: "Bus" },
  { id: "honest", label: "Honest" },
  { id: "generalisation", label: "Generalisation" },
];

export default function DemoPage() {
  return (
    <>
      <PageHeader
        eyebrow="Demo"
        title="The Arena"
        lead="Two controllers, the same junction, the same vehicles arriving at the same seconds. These are recordings of real simulation runs, replayed in your browser."
      />
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Arena network={network} scenes={SCENES} T={meta.reward.T ?? 90} corridor={corridor} />
      </div>
    </>
  );
}
