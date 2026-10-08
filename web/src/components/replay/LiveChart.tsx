"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { clock } from "@/lib/format";
import type { Replay } from "@/lib/types";

/** Mean accumulated wait on the approaches for both sides, with the playhead marked. */
export default function LiveChart({ replay, second }: { replay: Replay; second: number }) {
  const data = useMemo(() => {
    const left = replay.sides.left.series.wait_now;
    const right = replay.sides.right.series.wait_now;
    return left.map((v, i) => ({ t: i, left: v, right: right[i] }));
  }, [replay]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={[0, data.length - 1]}
          tickFormatter={(t: number) => clock(replay.t0 + t)}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          stroke="var(--line)"
          tickCount={6}
        />
        <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--line)" width={52} />
        <Tooltip
          isAnimationActive={false}
          contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "var(--muted)" }}
          labelFormatter={(t) => `t = ${clock(replay.t0 + Number(t))}`}
          formatter={(value, name) => [`${Number(value).toFixed(1)} s`, name === "left" ? "Left" : "Right"]}
        />
        {replay.events.map((e) => (
          <ReferenceLine key={e.t} x={e.t - replay.t0} stroke="var(--amber)" strokeDasharray="3 3" />
        ))}
        <ReferenceLine x={second} stroke="var(--text)" strokeOpacity={0.7} />
        <Line dataKey="left" stroke="var(--muted)" strokeWidth={1.6} dot={false} isAnimationActive={false} />
        <Line dataKey="right" stroke="var(--wave-b)" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
