"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { loadReplay } from "@/lib/replay/store";
import type { Network, ReplaySide } from "@/lib/types";
import { ReplayCanvas } from "./replay/ReplayCanvas";

const SPEED = 2;
const SMALL = "(max-width: 768px)";

function subscribeSmall(onChange: () => void): () => void {
  const query = window.matchMedia(SMALL);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/** Full-bleed loop of the hero replay (our agent only), behind the headline. */
export function HeroCanvas({ network }: { network: Network }) {
  const [side, setSide] = useState<ReplaySide | null>(null);
  const small = useSyncExternalStore(subscribeSmall, () => window.matchMedia(SMALL).matches, () => false);
  const fps = small ? 30 : 60;
  const start = useRef(0);
  const frozen = useRef(false);

  useEffect(() => {
    frozen.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cancelled = false;
    // Wait for idle time so the replay download never competes with first paint.
    const begin = () =>
      loadReplay("hero")
        .then((replay) => {
          if (cancelled) return;
          start.current = performance.now();
          setSide(replay.sides.right);
        })
        .catch(() => {});
    const idle = window.requestIdleCallback
      ? window.requestIdleCallback(begin, { timeout: 2500 })
      : window.setTimeout(begin, 1200);
    return () => {
      cancelled = true;
      if (window.cancelIdleCallback) window.cancelIdleCallback(idle);
      else window.clearTimeout(idle);
    };
  }, []);

  const getTime = useCallback(() => {
    if (!side) return 0;
    const duration = side.frames.length - 1;
    if (frozen.current) return Math.floor(duration / 2);
    return (((performance.now() - start.current) / 1000) * SPEED) % duration;
  }, [side]);

  return (
    <div aria-hidden className={`absolute inset-0 transition-opacity duration-1000 ${side ? "opacity-100" : "opacity-0"}`}>
      <ReplayCanvas network={network} side={side} getTime={getTime} maxFps={fps} label="" />
    </div>
  );
}
