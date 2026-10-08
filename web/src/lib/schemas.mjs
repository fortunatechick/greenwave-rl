// Data contract (spec 11.2). Mirrors greenwave/web_schema.py. Plain JS so that both the
// site (build time) and scripts/check-data.mjs (prebuild) validate with the same schemas.
import { z } from "zod";

const num = z.number().finite();
const point = z.tuple([num, num]);

export const MetaSchema = z.strictObject({
  mock: z.boolean(),
  profile: z.string(),
  generated_at: z.string(),
  git_sha: z.string(),
  synthetic_demand: z.boolean(),
  junction_name: z.string(),
  network_source: z.enum(["osm", "plain"]),
  sumo_version: z.string(),
  seeds: z.record(z.string(), z.number().int()),
  deviations: z.array(z.string()),
  headline: z.strictObject({
    regime: z.string(),
    metric: z.string(),
    rl: num.nullable(),
    fixed: num.nullable(),
    max_pressure: num.nullable(),
  }),
  kpis: z.array(
    z.strictObject({ key: z.string(), label: z.string(), value: num.nullable(), detail: z.string() }),
  ),
  honest_finding: z.string(),
  reward: z.record(z.string(), num),
  controllers: z.record(z.string(), z.string()),
});

export const NetworkSchema = z.strictObject({
  bounds: z.tuple([num, num, num, num]),
  lanes: z.array(
    z.strictObject({
      id: z.string(),
      approach: z.string(),
      dir: z.enum(["in", "out"]),
      width: num,
      shape: z.array(point).min(2),
    }),
  ),
  junction_shape: z.array(point).min(3),
  signals: z.array(
    z.strictObject({ approach: z.string(), pos: point, angle: num, link: z.number().int() }),
  ),
  approaches: z.array(z.string()),
  facts: z.record(z.string(), z.unknown()),
});

export const MainSchema = z.array(
  z.strictObject({
    regime: z.string(),
    controller: z.string(),
    metric: z.string(),
    mean: num,
    std: num,
    n: z.number().int(),
    p_vs_fixed: num.nullable(),
    p_vs_mp: num.nullable(),
  }),
);

export const CurvesSchema = z.record(
  z.string(),
  z.strictObject({
    steps: z.array(z.number().int()),
    mean: z.array(num),
    std: z.array(num),
    n_seeds: z.number().int(),
  }),
);

export const GeneralisationSchema = z.array(
  z.strictObject({
    metric: z.string(),
    regimes: z.array(z.string()),
    matrix: z.array(z.array(num)),
    std: z.array(z.array(num)),
    dr_row: z.array(num),
    dr_std: z.array(num),
    gap_recovered_pct: num.nullable(),
  }),
);

export const FairnessSchema = z.record(
  z.string(),
  z.strictObject({
    label: z.string(),
    regime: z.string(),
    ecdf_x: z.array(num),
    ecdf_y: z.array(num),
    p50: num,
    p95: num,
    max: num,
  }),
);

export const PerClassSchema = z.array(
  z.strictObject({
    regime: z.string(),
    controller: z.string(),
    class: z.string(),
    delay_mean: num,
    delay_std: num,
  }),
);

export const AblationsSchema = z.array(
  z.strictObject({
    group: z.string(),
    variant: z.string(),
    metric: z.string(),
    mean: num,
    std: num,
    n: z.number().int(),
    regime: z.string(),
    reference: z.boolean(),
    takeaway: z.string(),
  }),
);

export const DemandSchema = z.strictObject({
  regimes: z.record(
    z.string(),
    z.strictObject({
      pcu_per_hour: z.record(z.string(), num),
      veh_per_hour_by_approach: z.record(z.string(), num),
      veh_per_hour_by_class: z.record(z.string(), num),
      webster: z.strictObject({
        cycle: num,
        greens: z.record(z.string(), num),
        Y: num,
        saturation: z.record(z.string(), num),
      }),
    }),
  ),
  pcu: z.record(z.string(), num),
  passenger_weights: z.record(z.string(), num),
  class_mix: z.record(z.string(), num),
  classes: z.array(z.string()),
});

const SideSchema = z.strictObject({
  veh_class: z.array(z.number().int().min(0).max(3)),
  frames: z.array(z.array(z.number().int())),
  signal: z.array(z.string()),
  phase: z.array(z.number().int()),
  series: z.strictObject({
    wait_now: z.array(num),
    queue_by_approach: z.array(z.array(z.number().int())),
    person_wait_cum: z.array(num),
    max_wait: z.array(num),
  }),
});

export const ReplaySchema = z
  .strictObject({
    scene: z.string(),
    title: z.string(),
    caption: z.string(),
    left: z.strictObject({ controller: z.string(), label: z.string() }),
    right: z.strictObject({ controller: z.string(), label: z.string() }),
    regime: z.string(),
    seed: z.number().int(),
    t0: z.number().int(),
    t1: z.number().int(),
    dt: z.literal(1),
    classes: z.array(z.string()).length(4),
    events: z.array(z.strictObject({ t: z.number().int(), label: z.string() })),
    sides: z.strictObject({ left: SideSchema, right: SideSchema }),
    mock: z.boolean(),
  })
  .refine(
    (r) =>
      ["left", "right"].every((s) => {
        const side = r.sides[s];
        const n = r.t1 - r.t0;
        return (
          side.frames.length === n &&
          side.signal.length === n &&
          side.series.wait_now.length === n &&
          side.frames.every((f) => f.length % 4 === 0)
        );
      }),
    { message: "replay arrays must have one entry per second and 4 ints per vehicle" },
  );

export const SCENES = ["hero", "surge", "starvation", "bus", "honest", "generalisation"];

export const FILES = {
  "meta.json": MetaSchema,
  "network.json": NetworkSchema,
  "demand.json": DemandSchema,
  "results/main.json": MainSchema,
  "results/curves.json": CurvesSchema,
  "results/generalisation.json": GeneralisationSchema,
  "results/fairness.json": FairnessSchema,
  "results/per_class.json": PerClassSchema,
  "results/ablations.json": AblationsSchema,
};
