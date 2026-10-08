"use client";

import { useLayoutEffect, useSyncExternalStore } from "react";

type Theme = "light" | "dark";

function readTheme(): Theme {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

/** The current theme, kept in sync with the data-theme attribute on <html>. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, readTheme, () => "dark");
}

export function ThemeToggle() {
  const theme = useTheme();

  // React's dev-mode remount clears attributes it does not manage; re-apply the stored theme.
  useLayoutEffect(() => {
    try {
      const stored = localStorage.getItem("theme");
      if (stored === "light" || stored === "dark") document.documentElement.setAttribute("data-theme", stored);
    } catch {}
  }, []);

  function toggle() {
    const next: Theme = readTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-line bg-surface-1 text-muted transition-colors hover:text-text"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden suppressHydrationWarning>
        {theme === "dark" ? (
          <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7Z" fill="currentColor" />
        ) : (
          <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="8" cy="8" r="3" fill="currentColor" />
            <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1" />
          </g>
        )}
      </svg>
    </button>
  );
}
