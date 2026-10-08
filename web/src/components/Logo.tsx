/** Wordmark with a 3-dot vertical signal glyph; the bottom dot is the "go" colour. */
export function SignalGlyph({ size = 22 }: { size?: number }) {
  return (
    <svg width={size * 0.5} height={size} viewBox="0 0 12 24" aria-hidden>
      <rect x="0.5" y="0.5" width="11" height="23" rx="5.5" fill="var(--surface-2)" stroke="var(--line)" />
      <circle cx="6" cy="5.5" r="2.4" fill="var(--muted)" opacity="0.45" />
      <circle cx="6" cy="12" r="2.4" fill="var(--muted)" opacity="0.45" />
      <circle cx="6" cy="18.5" r="2.4" fill="var(--go)" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
      <SignalGlyph />
      <span>
        GreenWave<span className="ml-0.5 font-normal text-muted">-RL</span>
      </span>
    </span>
  );
}
