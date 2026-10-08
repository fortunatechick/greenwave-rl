import type { Network, ReplaySide } from "@/lib/types";

export type Palette = {
  bg: string;
  road: string;
  roadLine: string;
  text: string;
  muted: string;
  go: string;
  amber: string;
  stop: string;
  surface: string;
  line: string;
  veh: [string, string, string, string];
};

/** Length x width in metres per class: two_wheeler, auto_rickshaw, car, bus. */
const DIMS: [number, number][] = [
  [1.9, 0.8],
  [2.6, 1.4],
  [4.3, 1.8],
  [12.0, 2.5],
];
const FADE = 0.3; // vehicles fade in / out over 300 ms of replay time

export function readPalette(el: Element = document.documentElement): Palette {
  const css = getComputedStyle(el);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    bg: v("--bg"),
    road: v("--road"),
    roadLine: v("--road-line"),
    text: v("--text"),
    muted: v("--muted"),
    go: v("--go"),
    amber: v("--amber"),
    stop: v("--stop"),
    surface: v("--surface-2"),
    line: v("--line"),
    veh: [v("--veh-2w"), v("--veh-auto"), v("--veh-car"), v("--veh-bus")],
  };
}

/**
 * Draws one side of a replay. The road layer is rendered once per size to an offscreen
 * canvas; each frame only vehicles and signal heads are drawn on top.
 */
export class ReplayRenderer {
  private ctx: CanvasRenderingContext2D;
  private road: HTMLCanvasElement | null = null;
  private width = 0;
  private height = 0;
  private dpr = 1;
  private scale = 1;
  private ox = 0;
  private oy = 0;
  private slot: Int32Array = new Int32Array(0);
  private stamp: Int32Array = new Int32Array(0);
  private tick = 0;
  side: ReplaySide | null = null;
  highlightBuses = false;

  constructor(
    private canvas: HTMLCanvasElement,
    private network: Network,
    private palette: Palette,
  ) {
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("2D canvas is not available");
    this.ctx = ctx;
  }

  setSide(side: ReplaySide | null): void {
    this.side = side;
    const n = side ? side.veh_class.length : 0;
    this.slot = new Int32Array(n);
    this.stamp = new Int32Array(n);
    this.tick = 0;
  }

  setPalette(palette: Palette): void {
    this.palette = palette;
    this.road = null;
  }

  resize(cssWidth: number, cssHeight: number): void {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (cssWidth === this.width && cssHeight === this.height && dpr === this.dpr) return;
    this.width = cssWidth;
    this.height = cssHeight;
    this.dpr = dpr;
    this.canvas.width = Math.max(1, Math.round(cssWidth * dpr));
    this.canvas.height = Math.max(1, Math.round(cssHeight * dpr));
    const [x0, y0, x1, y1] = this.network.bounds;
    const pad = 4;
    // Cover the canvas: the junction stays centred and the longer axis shows more road.
    this.scale = Math.max((cssWidth - pad) / (x1 - x0), (cssHeight - pad) / (y1 - y0)) * 1.0;
    const minSide = Math.min(cssWidth, cssHeight);
    this.scale = Math.max(this.scale, minSide / 190);
    this.ox = cssWidth / 2 - ((x0 + x1) / 2) * this.scale;
    this.oy = cssHeight / 2 + ((y0 + y1) / 2) * this.scale;
    this.road = null;
  }

  private sx(x: number): number {
    return this.ox + x * this.scale;
  }

  private sy(y: number): number {
    return this.oy - y * this.scale; // world y points up, canvas y points down
  }

  private buildRoad(): HTMLCanvasElement {
    const layer = document.createElement("canvas");
    layer.width = this.canvas.width;
    layer.height = this.canvas.height;
    const c = layer.getContext("2d")!;
    const p = this.palette;
    c.scale(this.dpr, this.dpr);
    c.lineCap = "butt";
    c.lineJoin = "round";

    const path = (shape: readonly (readonly [number, number])[]) => {
      c.beginPath();
      shape.forEach(([x, y], i) => (i ? c.lineTo(this.sx(x), this.sy(y)) : c.moveTo(this.sx(x), this.sy(y))));
    };
    // Lane separators show through as the gap between slightly narrowed lane strokes.
    c.strokeStyle = p.roadLine;
    for (const lane of this.network.lanes) {
      path(lane.shape);
      c.lineWidth = (lane.width + 0.25) * this.scale;
      c.stroke();
    }
    c.strokeStyle = p.road;
    for (const lane of this.network.lanes) {
      path(lane.shape);
      c.lineWidth = Math.max(1, (lane.width - 0.18) * this.scale);
      c.stroke();
    }
    path(this.network.junction_shape);
    c.closePath();
    c.fillStyle = p.road;
    c.fill();

    // Stop lines at the end of every incoming lane.
    c.strokeStyle = p.text;
    c.globalAlpha = 0.55;
    c.lineWidth = Math.max(1, 0.45 * this.scale);
    for (const lane of this.network.lanes) {
      if (lane.dir !== "in") continue;
      const [x1, y1] = lane.shape[lane.shape.length - 1];
      const [x0, y0] = lane.shape[lane.shape.length - 2];
      const len = Math.hypot(x1 - x0, y1 - y0) || 1;
      const nx = (-(y1 - y0) / len) * (lane.width / 2 - 0.2);
      const ny = ((x1 - x0) / len) * (lane.width / 2 - 0.2);
      c.beginPath();
      c.moveTo(this.sx(x1 + nx), this.sy(y1 + ny));
      c.lineTo(this.sx(x1 - nx), this.sy(y1 - ny));
      c.stroke();
    }
    c.globalAlpha = 1;
    return layer;
  }

  private vehicle(cls: number, x: number, y: number, angleDeg: number, alpha: number): void {
    const c = this.ctx;
    const [len, wid] = DIMS[cls];
    const l = Math.max(len * this.scale, cls === 3 ? 7 : 3);
    const w = Math.max(wid * this.scale, cls === 0 ? 1.6 : 2.2);
    const dim = this.highlightBuses && cls !== 3 ? 0.18 : 1;
    c.globalAlpha = alpha * dim;
    c.fillStyle = this.palette.veh[cls];
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.translate(this.sx(x), this.sy(y));
    c.rotate((angleDeg * Math.PI) / 180);
    // SUMO positions are the front bumper; the body extends backwards (+y after rotation).
    const radius = cls === 0 ? w / 2 : cls === 1 ? w * 0.38 : Math.min(1.5, w * 0.2);
    c.beginPath();
    c.roundRect(-w / 2, 0, w, l, radius);
    c.fill();
    if (this.highlightBuses && cls === 3) {
      c.globalAlpha = alpha;
      c.strokeStyle = this.palette.text;
      c.lineWidth = 1;
      c.stroke();
    }
  }

  private signals(state: string): void {
    const c = this.ctx;
    const p = this.palette;
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.globalAlpha = 1;
    const r = Math.max(2.4, Math.min(4.2, this.scale * 1.1));
    for (const sig of this.network.signals) {
      const a = (sig.angle * Math.PI) / 180;
      // Kerb side in left-hand traffic is to the left of the direction of travel.
      const half = this.network.lanes.filter((l) => l.approach === sig.approach && l.dir === "in").length * 1.75;
      const px = this.sx(sig.pos[0] - Math.cos(a) * (half + 3.5) - Math.sin(a) * 2);
      const py = this.sy(sig.pos[1] + Math.sin(a) * (half + 3.5) - Math.cos(a) * 2);
      const ch = state[sig.link] ?? "r";
      const lit = ch === "G" || ch === "g" ? 2 : ch === "y" || ch === "Y" ? 1 : 0;
      c.fillStyle = p.surface;
      c.strokeStyle = p.line;
      c.lineWidth = 1;
      c.beginPath();
      c.roundRect(px - r * 1.6, py - r * 4, r * 3.2, r * 8, r * 1.6);
      c.fill();
      c.stroke();
      const colours = [p.stop, p.amber, p.go];
      for (let i = 0; i < 3; i++) {
        c.beginPath();
        c.arc(px, py - r * 2.4 + i * r * 2.4, r * 0.9, 0, Math.PI * 2);
        c.fillStyle = i === lit ? colours[i] : p.muted;
        c.globalAlpha = i === lit ? 1 : 0.28;
        c.fill();
      }
      c.globalAlpha = 1;
    }
  }

  /** Draw the replay at `time` seconds from the start of the recording window. */
  draw(time: number): void {
    const c = this.ctx;
    if (!this.width || !this.height) return;
    if (!this.road) this.road = this.buildRoad();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1;
    c.clearRect(0, 0, this.canvas.width, this.canvas.height);
    c.drawImage(this.road, 0, 0);
    const side = this.side;
    if (!side || side.frames.length === 0) return;

    const last = side.frames.length - 1;
    const t = Math.min(Math.max(time, 0), last);
    const f0 = Math.floor(t);
    const f1 = Math.min(f0 + 1, last);
    const frac = t - f0;
    const a = side.frames[f0];
    const b = side.frames[f1];
    const cls = side.veh_class;

    // Index frame b by vehicle so each vehicle of frame a finds its next position in O(1).
    const tick = ++this.tick;
    for (let i = 0; i < b.length; i += 4) {
      this.slot[b[i]] = i;
      this.stamp[b[i]] = tick;
    }
    for (let i = 0; i < a.length; i += 4) {
      const id = a[i];
      if (this.stamp[id] === tick) {
        const k = this.slot[id];
        this.stamp[id] = -tick; // consumed
        let da = b[k + 3] - a[i + 3];
        if (da > 180) da -= 360;
        else if (da < -180) da += 360; // shortest arc
        this.vehicle(
          cls[id],
          (a[i + 1] + (b[k + 1] - a[i + 1]) * frac) / 10,
          (a[i + 2] + (b[k + 2] - a[i + 2]) * frac) / 10,
          a[i + 3] + da * frac,
          1,
        );
      } else {
        const alpha = 1 - frac / FADE; // left the view: fade out
        if (alpha > 0) this.vehicle(cls[id], a[i + 1] / 10, a[i + 2] / 10, a[i + 3], alpha);
      }
    }
    for (let i = 0; i < b.length; i += 4) {
      if (this.stamp[b[i]] === tick) {
        const alpha = (frac - (1 - FADE)) / FADE; // entering: fade in
        if (alpha > 0) this.vehicle(cls[b[i]], b[i + 1] / 10, b[i + 2] / 10, b[i + 3], Math.min(alpha, 1));
      }
    }
    this.signals(side.signal[f0]);
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1;
  }
}
