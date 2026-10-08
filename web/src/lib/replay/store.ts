import { create } from "zustand";
import type { Replay } from "@/lib/types";

export const SPEEDS = [1, 4, 16] as const;

type ArenaState = {
  scene: string;
  replay: Replay | null;
  status: "idle" | "loading" | "ready" | "error";
  /** Seconds from the start of the recording window. One clock drives both canvases and the charts. */
  time: number;
  playing: boolean;
  speed: number;
  busHighlight: boolean;
  setScene: (scene: string) => void;
  setReplay: (replay: Replay | null, status: ArenaState["status"]) => void;
  seek: (time: number) => void;
  nudge: (delta: number) => void;
  toggle: () => void;
  setPlaying: (playing: boolean) => void;
  setSpeed: (speed: number) => void;
  setBusHighlight: (on: boolean) => void;
};

const clamp = (t: number, replay: Replay | null) =>
  Math.min(Math.max(t, 0), replay ? replay.t1 - replay.t0 - 1 : 0);

export const useArena = create<ArenaState>((set) => ({
  scene: "hero",
  replay: null,
  status: "idle",
  time: 0,
  playing: false,
  speed: 4,
  busHighlight: false,
  setScene: (scene) => set({ scene, time: 0, replay: null, status: "loading" }),
  setReplay: (replay, status) => set({ replay, status, time: 0 }),
  seek: (time) => set((s) => ({ time: clamp(time, s.replay) })),
  nudge: (delta) => set((s) => ({ time: clamp(s.time + delta, s.replay) })),
  toggle: () =>
    set((s) => {
      const end = s.replay ? s.replay.t1 - s.replay.t0 - 1 : 0;
      // Pressing play at the end restarts the scene.
      return s.time >= end && !s.playing ? { playing: true, time: 0 } : { playing: !s.playing };
    }),
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  setBusHighlight: (busHighlight) => set({ busHighlight }),
}));

const cache = new Map<string, Promise<Replay>>();

/** Replays are fetched lazily on the client and cached per scene. */
export function loadReplay(scene: string): Promise<Replay> {
  let pending = cache.get(scene);
  if (!pending) {
    pending = fetch(`/data/replays/${scene}.json`).then((res) => {
      if (!res.ok) throw new Error(`replay ${scene}: HTTP ${res.status}`);
      return res.json() as Promise<Replay>;
    });
    pending.catch(() => cache.delete(scene));
    cache.set(scene, pending);
  }
  return pending;
}
