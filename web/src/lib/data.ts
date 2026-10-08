// Build-time data access. Import only from Server Components: the JSON is validated
// here with zod and passed down as props, so neither zod nor the raw files reach the client.
import ablationsJson from "../../public/data/results/ablations.json";
import curvesJson from "../../public/data/results/curves.json";
import demandJson from "../../public/data/demand.json";
import fairnessJson from "../../public/data/results/fairness.json";
import generalisationJson from "../../public/data/results/generalisation.json";
import mainJson from "../../public/data/results/main.json";
import metaJson from "../../public/data/meta.json";
import networkJson from "../../public/data/network.json";
import perClassJson from "../../public/data/results/per_class.json";
import {
  AblationsSchema,
  CurvesSchema,
  DemandSchema,
  FairnessSchema,
  GeneralisationSchema,
  MainSchema,
  MetaSchema,
  NetworkSchema,
  PerClassSchema,
} from "./schemas.mjs";
import type { MainRow } from "./types";

export const meta = MetaSchema.parse(metaJson);
export const network = NetworkSchema.parse(networkJson);
export const demand = DemandSchema.parse(demandJson);
export const main = MainSchema.parse(mainJson);
export const curves = CurvesSchema.parse(curvesJson);
export const generalisation = GeneralisationSchema.parse(generalisationJson);
export const fairness = FairnessSchema.parse(fairnessJson);
export const perClass = PerClassSchema.parse(perClassJson);
export const ablations = AblationsSchema.parse(ablationsJson);

export function mainValue(regime: string, controller: string, metric: string): MainRow | undefined {
  return main.find((r) => r.regime === regime && r.controller === controller && r.metric === metric);
}

export function controllerLabel(key: string): string {
  return meta.controllers[key] ?? key;
}

/** Controllers present in main.json, in a stable display order. */
export const CONTROLLER_ORDER = [
  "fixed_peak",
  "fixed_matched",
  "actuated",
  "max_pressure",
  "dqn_sb3",
  "ppo",
  "ddqn_fair",
  "ddqn_fair_dr",
  "random",
].filter((c) => main.some((r) => r.controller === c));

export const OURS = new Set(["ddqn_fair", "ddqn_fair_dr"]);

export const siteUrl = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://greenwave-rl.vercel.app").replace(/\/$/, "");
export const repoUrl = process.env.NEXT_PUBLIC_REPO_URL ?? "https://github.com/Om-Chaudhari/greenwave-rl";
