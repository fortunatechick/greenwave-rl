"use client";

import { useEffect, useRef } from "react";
import { ReplayRenderer, readPalette } from "@/lib/replay/renderer";
import type { Network, ReplaySide } from "@/lib/types";
import { useTheme } from "../ThemeToggle";

type Props = {
  network: Network;
  side: ReplaySide | null;
  /** Returns the current replay time; called every animation frame while visible. */
  getTime: () => number;
  highlightBuses?: boolean;
  label: string;
  className?: string;
  /** Cap the redraw rate (the hero uses 30 fps on small screens). */
  maxFps?: number;
};

/** One replay canvas, sized to its container. Pauses when off-screen or when the tab is hidden. */
export function ReplayCanvas({ network, side, getTime, highlightBuses = false, label, className, maxFps = 60 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<ReplayRenderer | null>(null);
  const getTimeRef = useRef(getTime);
  const theme = useTheme();

  useEffect(() => {
    getTimeRef.current = getTime;
  }, [getTime]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const renderer = new ReplayRenderer(canvas, network, readPalette());
    rendererRef.current = renderer;

    let visible = true;
    let frame = 0;
    let lastDraw = 0;
    let lastTime = -1;
    let dirty = true;
    const minGap = 1000 / maxFps - 2;

    const loop = (now: number) => {
      frame = requestAnimationFrame(loop);
      if (!visible || document.hidden || now - lastDraw < minGap) return;
      const t = getTimeRef.current();
      if (t === lastTime && !dirty) return; // paused and unchanged: nothing to redraw
      lastTime = t;
      lastDraw = now;
      dirty = false;
      renderer.draw(t);
    };

    const resize = new ResizeObserver(([entry]) => {
      renderer.resize(entry.contentRect.width, entry.contentRect.height);
      dirty = true;
    });
    resize.observe(canvas);
    const intersect = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      dirty = true;
    });
    intersect.observe(canvas);
    const markDirty = () => {
      dirty = true;
    };
    canvas.addEventListener("replay:dirty", markDirty);
    frame = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      intersect.disconnect();
      canvas.removeEventListener("replay:dirty", markDirty);
      rendererRef.current = null;
    };
  }, [network, maxFps]);

  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.setSide(side);
    renderer.highlightBuses = highlightBuses;
    renderer.setPalette(readPalette());
    canvasRef.current?.dispatchEvent(new Event("replay:dirty"));
  }, [side, highlightBuses, theme]);

  return <canvas ref={canvasRef} role="img" aria-label={label} className={`block h-full w-full ${className ?? ""}`} />;
}
