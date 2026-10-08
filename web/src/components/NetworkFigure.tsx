import type { Network } from "@/lib/types";

/** Static plan view of the junction, drawn from network.json. */
export function NetworkFigure({ network, half = 90 }: { network: Network; half?: number }) {
  const size = 480;
  const k = size / (2 * half);
  const px = (x: number) => size / 2 + x * k;
  const py = (y: number) => size / 2 - y * k;
  const pts = (shape: readonly (readonly [number, number])[]) => shape.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join(" ");
  const labelAt: Record<string, [number, number]> = { N: [0, half - 9], E: [half - 9, 0], S: [0, -half + 9], W: [-half + 9, 0] };
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full rounded-[10px] bg-bg" role="img"
      aria-label="Plan view of the simulated junction showing every lane and the direction of travel">
      {network.lanes.map((l) => (
        <polyline key={`b${l.id}`} points={pts(l.shape)} fill="none" stroke="var(--road-line)" strokeWidth={(l.width + 0.25) * k} />
      ))}
      {network.lanes.map((l) => (
        <polyline key={l.id} points={pts(l.shape)} fill="none" stroke="var(--road)" strokeWidth={(l.width - 0.18) * k} />
      ))}
      <polygon points={pts(network.junction_shape)} fill="var(--road)" />
      {network.lanes.filter((l) => l.dir === "in").map((l) => {
        const [x1, y1] = l.shape[l.shape.length - 1];
        const [x0, y0] = l.shape[l.shape.length - 2];
        const len = Math.hypot(x1 - x0, y1 - y0) || 1;
        const ux = (x1 - x0) / len, uy = (y1 - y0) / len;
        const bx = x1 - ux * 16, by = y1 - uy * 16; // arrow drawn 16 m before the stop line
        return (
          <g key={`a${l.id}`} stroke="var(--muted)" strokeWidth="1.4" fill="none">
            <line x1={px(bx - ux * 5)} y1={py(by - uy * 5)} x2={px(bx + ux * 5)} y2={py(by + uy * 5)} />
            <polyline points={`${px(bx + ux * 2 - uy * 1.2)},${py(by + uy * 2 + ux * 1.2)} ${px(bx + ux * 5)},${py(by + uy * 5)} ${px(bx + ux * 2 + uy * 1.2)},${py(by + uy * 2 - ux * 1.2)}`} />
          </g>
        );
      })}
      {network.approaches.map((a) => (
        <text key={a} x={px(labelAt[a]?.[0] ?? 0)} y={py(labelAt[a]?.[1] ?? 0) + 5} textAnchor="middle" fontSize="15"
          fill="var(--text)" className="num" fontWeight="600"
          dx={a === "N" ? -34 : a === "S" ? 34 : 0} dy={a === "E" ? -30 : a === "W" ? 30 : 0}>{a}</text>
      ))}
    </svg>
  );
}
