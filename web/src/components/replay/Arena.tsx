"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { clock, fmt } from "@/lib/format";
import { SPEEDS, loadReplay, useArena } from "@/lib/replay/store";
import type { Network, Replay, ReplaySide } from "@/lib/types";
import { CLASS_LABEL } from "@/lib/types";
import { ReplayCanvas } from "./ReplayCanvas";

const LiveChart = dynamic(() => import("./LiveChart"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center text-sm text-muted">Loading chart…</div>,
});

export type SceneInfo = { id: string; label: string };

const getTime = () => useArena.getState().time;

/** One requestAnimationFrame clock for the whole arena. */
function useClock() {
  useEffect(() => {
    let frame = 0;
    let last = performance.now();
    const loop = (now: number) => {
      frame = requestAnimationFrame(loop);
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      const s = useArena.getState();
      if (!s.playing || !s.replay || document.hidden) return;
      const end = s.replay.t1 - s.replay.t0 - 1;
      const next = s.time + dt * s.speed;
      if (next >= end) useArena.setState({ time: end, playing: false });
      else useArena.setState({ time: next });
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, []);
}

function phaseAge(side: ReplaySide, second: number): number {
  let age = 0;
  for (let i = second; i >= 0 && side.phase[i] === side.phase[second]; i--) age++;
  return age;
}

function Hud({ side, second, approaches, T }: { side: ReplaySide; second: number; approaches: string[]; T: number }) {
  const maxWait = side.series.max_wait[second] ?? 0;
  const phase = side.phase[second] ?? 0;
  const tone = maxWait > 1.5 * T ? "text-stop" : maxWait > T ? "text-amber" : "text-text";
  return (
    <div className="pointer-events-none absolute inset-x-2 top-2 flex flex-wrap items-start justify-between gap-2 text-[11px] sm:text-xs">
      <div className="rounded-md border border-line bg-bg/80 px-2 py-1 backdrop-blur">
        <span className="text-muted">Green </span>
        <span key={phase} className="num phase-pulse inline-block rounded-sm px-1 font-semibold">
          {approaches[phase]}
        </span>
        <span className="num text-muted"> · {phaseAge(side, second)} s</span>
      </div>
      <div className="rounded-md border border-line bg-bg/80 px-2 py-1 backdrop-blur">
        <span className="text-muted">Longest wait </span>
        <span className={`num font-semibold ${tone}`}>{fmt(maxWait, 0)} s</span>
      </div>
    </div>
  );
}

function QueueBars({ replay, second, approaches }: { replay: Replay; second: number; approaches: string[] }) {
  const max = useMemo(() => {
    let m = 1;
    for (const side of [replay.sides.left, replay.sides.right])
      for (const row of side.series.queue_by_approach) for (const v of row) if (v > m) m = v;
    return m;
  }, [replay]);
  const left = replay.sides.left.series.queue_by_approach[second] ?? [];
  const right = replay.sides.right.series.queue_by_approach[second] ?? [];
  return (
    <div className="grid grid-cols-4 gap-3">
      {approaches.map((a, i) => (
        <div key={a}>
          <div className="flex h-28 items-end justify-center gap-1.5">
            {[left[i] ?? 0, right[i] ?? 0].map((v, k) => (
              <div key={k} className="flex h-full w-5 flex-col justify-end sm:w-7">
                <span className="num mb-0.5 text-center text-[10px] text-muted">{v}</span>
                <div
                  className={`rounded-t-sm ${k === 0 ? "bg-muted/70" : "bg-gradient-to-t from-wave-a to-wave-b"}`}
                  style={{ height: `${(v / max) * 82}%`, minHeight: 2 }}
                />
              </div>
            ))}
          </div>
          <p className="num mt-1 text-center text-xs text-muted">{a}</p>
        </div>
      ))}
    </div>
  );
}

const SHAPES = [
  { key: "two_wheeler", w: 14, h: 5, r: 2.5, c: "var(--veh-2w)" },
  { key: "auto_rickshaw", w: 14, h: 8, r: 3, c: "var(--veh-auto)" },
  { key: "car", w: 20, h: 9, r: 1.5, c: "var(--veh-car)" },
  { key: "bus", w: 38, h: 9, r: 1.5, c: "var(--veh-bus)" },
];

export function ClassLegend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted" aria-label="Vehicle classes">
      {SHAPES.map((s) => (
        <li key={s.key} className="flex items-center gap-1.5">
          <svg width={s.w} height={10} aria-hidden>
            <rect x={0} y={(10 - s.h) / 2} width={s.w} height={s.h} rx={s.r} fill={s.c} />
          </svg>
          {CLASS_LABEL[s.key]}
        </li>
      ))}
    </ul>
  );
}

export function Arena({ network, scenes, T }: { network: Network; scenes: SceneInfo[]; T: number }) {
  useClock();
  const scene = useArena((s) => s.scene);
  const replay = useArena((s) => s.replay);
  const status = useArena((s) => s.status);
  const playing = useArena((s) => s.playing);
  const speed = useArena((s) => s.speed);
  const busHighlight = useArena((s) => s.busHighlight);
  const second = useArena((s) => Math.floor(s.time));
  const { setScene, setReplay, seek, nudge, toggle, setSpeed, setBusHighlight } = useArena.getState();
  const [chartSecond, setChartSecond] = useState(0);
  const lastChart = useRef(0);

  // The chart re-renders at most ~8 times a second, whatever the playback speed.
  useEffect(() => {
    const now = performance.now();
    if (now - lastChart.current > 120 || !playing) {
      lastChart.current = now;
      setChartSecond(second);
    }
  }, [second, playing]);

  useEffect(() => {
    let cancelled = false;
    useArena.setState({ status: "loading", replay: null, time: 0 });
    loadReplay(scene)
      .then((r) => !cancelled && setReplay(r, "ready"))
      .catch(() => !cancelled && setReplay(null, "error"));
    return () => {
      cancelled = true;
    };
  }, [scene, setReplay]);

  const pick = useCallback(
    (id: string) => {
      setBusHighlight(id === "bus");
      setScene(id);
    },
    [setScene, setBusHighlight],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA")) {
        if (!(el instanceof HTMLInputElement && el.type === "range" && e.key === " ")) return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === " ") {
        if (el?.tagName === "BUTTON") return; // let the focused button act
        e.preventDefault();
        toggle();
      } else if (e.key === "ArrowLeft") nudge(-10);
      else if (e.key === "ArrowRight") nudge(10);
      else if (e.key === "1" || e.key === "2" || e.key === "3") setSpeed(SPEEDS[Number(e.key) - 1]);
      else if (e.key === "b" || e.key === "B") setBusHighlight(!useArena.getState().busHighlight);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle, nudge, setSpeed, setBusHighlight]);

  const duration = replay ? replay.t1 - replay.t0 - 1 : 0;
  const approaches = network.approaches;
  const sides = replay ? ([["left", replay.left, replay.sides.left], ["right", replay.right, replay.sides.right]] as const) : [];

  return (
    <div className="space-y-5">
      <div role="tablist" aria-label="Scenes" className="flex flex-wrap gap-2">
        {scenes.map((s) => (
          <button
            key={s.id}
            role="tab"
            type="button"
            aria-selected={scene === s.id}
            onClick={() => pick(s.id)}
            className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
              scene === s.id ? "border-wave-b bg-wave-b/10 text-text" : "border-line text-muted hover:text-text"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="min-h-[3.25rem]">
        {replay ? (
          <>
            <h2 className="text-lg font-semibold">
              {replay.title}
              {replay.mock ? <span className="ml-2 text-sm font-normal text-amber">(preview recording)</span> : null}
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-muted">{replay.caption}</p>
          </>
        ) : (
          <p className="text-sm text-muted" role="status">
            {status === "error" ? "This replay could not be loaded." : "Loading replay…"}
          </p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(replay ? sides : ([["left"], ["right"]] as const)).map((entry) => {
          const [key, info, side] = entry as readonly [string, Replay["left"] | undefined, ReplaySide | undefined];
          return (
            <figure key={key} className="card overflow-hidden">
              <figcaption className="flex items-baseline justify-between gap-3 border-b border-line px-3 py-2 text-sm">
                <span className="num text-xs uppercase tracking-wider text-muted">{key}</span>
                <span className={`truncate font-medium ${key === "right" ? "wave-text" : ""}`}>{info?.label ?? "…"}</span>
              </figcaption>
              <div className="relative aspect-square max-h-[70vh] w-full bg-bg">
                <ReplayCanvas
                  network={network}
                  side={side ?? null}
                  getTime={getTime}
                  highlightBuses={busHighlight}
                  label={`${key} simulation: ${info?.label ?? "loading"}`}
                />
                {side ? <Hud side={side} second={second} approaches={approaches} T={T} /> : null}
              </div>
            </figure>
          );
        })}
      </div>

      {/* Transport bar */}
      <div className="card flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:gap-4 sm:p-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggle}
            disabled={!replay}
            aria-label={playing ? "Pause" : "Play"}
            className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-wave-a to-wave-b text-[#04130b] disabled:opacity-40"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              {playing ? <path d="M3 2h3v10H3zM8 2h3v10H8z" fill="currentColor" /> : <path d="M3 1.5v11l9-5.5z" fill="currentColor" />}
            </svg>
          </button>
          <div role="group" aria-label="Playback speed" className="flex overflow-hidden rounded-md border border-line">
            {SPEEDS.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={speed === s}
                onClick={() => setSpeed(s)}
                className={`num px-2.5 py-1.5 text-xs ${speed === s ? "bg-surface-2 text-text" : "text-muted hover:text-text"}`}
              >
                {s}×
              </button>
            ))}
          </div>
        </div>
        <div className="relative flex-1">
          <input
            type="range"
            min={0}
            max={Math.max(duration, 1)}
            step={1}
            value={second}
            disabled={!replay}
            onChange={(e) => seek(Number(e.target.value))}
            aria-label="Replay position"
            aria-valuetext={replay ? `simulation time ${clock(replay.t0 + second)}` : undefined}
            className="h-2 w-full cursor-pointer accent-[var(--wave-b)]"
          />
          {replay?.events.map((e) => (
            <span
              key={e.t}
              title={e.label}
              className="pointer-events-none absolute top-full mt-0.5 -translate-x-1/2 whitespace-nowrap text-[10px] text-amber"
              style={{ left: `${((e.t - replay.t0) / Math.max(duration, 1)) * 100}%` }}
            >
              ▲ <span className="hidden sm:inline">{e.label}</span>
            </span>
          ))}
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="num text-sm" aria-live="off">
            t = {clock((replay?.t0 ?? 0) + second)}
          </span>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              role="switch"
              checked={busHighlight}
              onChange={(e) => setBusHighlight(e.target.checked)}
              className="h-4 w-4 accent-[var(--veh-bus)]"
            />
            Highlight buses
          </label>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ClassLegend />
        <p className="text-xs text-muted">
          <kbd className="num rounded border border-line px-1">Space</kbd> play/pause ·{" "}
          <kbd className="num rounded border border-line px-1">←</kbd>
          <kbd className="num rounded border border-line px-1">→</kbd> ±10 s ·{" "}
          <kbd className="num rounded border border-line px-1">1</kbd>
          <kbd className="num rounded border border-line px-1">2</kbd>
          <kbd className="num rounded border border-line px-1">3</kbd> speed ·{" "}
          <kbd className="num rounded border border-line px-1">B</kbd> buses
        </p>
      </div>

      {replay ? (
        <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
          <div className="card p-4">
            <div className="mb-2 flex items-baseline justify-between gap-3">
              <h3 className="text-sm font-medium">Mean wait of vehicles on the approaches (s)</h3>
              <p className="num text-xs text-muted">
                <span className="mr-3">— left</span>
                <span className="wave-text">— right</span>
              </p>
            </div>
            <div className="h-52">
              <LiveChart replay={replay} second={chartSecond} />
            </div>
          </div>
          <div className="card p-4">
            <div className="mb-2 flex items-baseline justify-between gap-3">
              <h3 className="text-sm font-medium">Queue per approach (vehicles)</h3>
              <p className="num text-xs text-muted">grey left · green right</p>
            </div>
            <QueueBars replay={replay} second={second} approaches={approaches} />
          </div>
        </div>
      ) : null}

      {replay ? (
        <p className="text-sm text-muted">
          Text summary: at simulation time {clock(replay.t0 + second)}, vehicles on the approaches have waited on
          average {fmt(replay.sides.left.series.wait_now[second])} s under {replay.left.label} and{" "}
          {fmt(replay.sides.right.series.wait_now[second])} s under {replay.right.label}. Cumulative waiting since the
          start of the clip: {fmt(replay.sides.left.series.person_wait_cum[second], 0)} against{" "}
          {fmt(replay.sides.right.series.person_wait_cum[second], 0)} person-minutes. Both sides receive identical
          arrivals (regime {replay.regime}, seed {replay.seed}).
        </p>
      ) : null}
    </div>
  );
}
