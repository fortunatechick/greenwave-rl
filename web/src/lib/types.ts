import type { z } from "zod";
import type {
  AblationsSchema,
  CorridorSchema,
  CurvesSchema,
  DemandSchema,
  FairnessSchema,
  GeneralisationSchema,
  MainSchema,
  MetaSchema,
  NetworkSchema,
  PerClassSchema,
  ReplaySchema,
} from "./schemas.mjs";

export type Meta = z.infer<typeof MetaSchema>;
export type Network = z.infer<typeof NetworkSchema>;
export type MainRow = z.infer<typeof MainSchema>[number];
export type Curves = z.infer<typeof CurvesSchema>;
export type Generalisation = z.infer<typeof GeneralisationSchema>[number];
export type Fairness = z.infer<typeof FairnessSchema>;
export type PerClassRow = z.infer<typeof PerClassSchema>[number];
export type AblationRow = z.infer<typeof AblationsSchema>[number];
export type Demand = z.infer<typeof DemandSchema>;
export type Corridor = z.infer<typeof CorridorSchema>;
export type Replay = z.infer<typeof ReplaySchema>;
export type ReplaySide = Replay["sides"]["left"];

export const REGIMES = ["low", "peak", "skewed", "surge"] as const;
export type Regime = (typeof REGIMES)[number];

export const REGIME_LABEL: Record<string, string> = {
  low: "Low",
  peak: "Peak",
  skewed: "Skewed",
  surge: "Surge",
};

export const CLASS_LABEL: Record<string, string> = {
  two_wheeler: "Two-wheeler",
  auto_rickshaw: "Auto-rickshaw",
  car: "Car",
  bus: "Bus",
};

export type MetricInfo = { label: string; unit: string; lowerIsBetter: boolean; digits: number };

export const METRICS: Record<string, MetricInfo> = {
  person_wait: { label: "Wait per person", unit: "s", lowerIsBetter: true, digits: 1 },
  veh_wait: { label: "Wait per vehicle", unit: "s", lowerIsBetter: true, digits: 1 },
  avg_queue: { label: "Avg queue", unit: "veh", lowerIsBetter: true, digits: 1 },
  throughput: { label: "Throughput", unit: "veh/h", lowerIsBetter: false, digits: 0 },
  max_wait: { label: "Max wait", unit: "s", lowerIsBetter: true, digits: 0 },
  wait_p95: { label: "Wait p95", unit: "s", lowerIsBetter: true, digits: 0 },
  co2: { label: "CO2", unit: "g/veh", lowerIsBetter: true, digits: 0 },
  delay_bus: { label: "Bus delay", unit: "s", lowerIsBetter: true, digits: 1 },
};

export const TABLE_METRICS = [
  "person_wait",
  "veh_wait",
  "avg_queue",
  "throughput",
  "max_wait",
  "wait_p95",
  "co2",
] as const;
