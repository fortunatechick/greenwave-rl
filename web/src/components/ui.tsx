import type { ReactNode } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

export function Badge({ children, tone = "muted" }: { children: ReactNode; tone?: "muted" | "amber" | "go" | "stop" }) {
  const tones = {
    muted: "border-line text-muted",
    amber: "border-amber/40 text-amber",
    go: "border-go/40 text-go",
    stop: "border-stop/40 text-stop",
  } as const;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function Section({ children, id, className = "" }: { children: ReactNode; id?: string; className?: string }) {
  return (
    <section id={id} className={`mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20 ${className}`}>
      {children}
    </section>
  );
}

export function SectionHeading({ eyebrow, title, lead }: { eyebrow?: string; title: ReactNode; lead?: ReactNode }) {
  return (
    <div className="mb-8 max-w-3xl sm:mb-10">
      {eyebrow ? <p className="num mb-3 text-xs uppercase tracking-[0.18em] text-muted">{eyebrow}</p> : null}
      <h2 className="h2 font-semibold">{title}</h2>
      {lead ? <p className="mt-3 text-base leading-relaxed text-muted sm:text-lg">{lead}</p> : null}
    </div>
  );
}

export function PageHeader({ eyebrow, title, lead }: { eyebrow: string; title: ReactNode; lead: ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-2 pt-12 sm:px-6 sm:pt-16">
      <p className="num mb-3 text-xs uppercase tracking-[0.18em] text-muted">{eyebrow}</p>
      <h1 className="text-[clamp(2rem,1.3rem+3vw,3.5rem)] font-semibold leading-[1.05] tracking-tight">{title}</h1>
      <p className="mt-4 max-w-3xl text-base leading-relaxed text-muted sm:text-lg">{lead}</p>
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card p-5 sm:p-6 ${className}`}>{children}</div>;
}

export function Callout({ title, children, tone = "wave" }: { title: string; children: ReactNode; tone?: "wave" | "amber" }) {
  const bar = tone === "amber" ? "bg-amber" : "bg-gradient-to-b from-wave-a to-wave-b";
  return (
    <aside className="card relative overflow-hidden p-5 pl-7 sm:p-6 sm:pl-8">
      <span aria-hidden className={`absolute inset-y-0 left-0 w-1 ${bar}`} />
      <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted">{title}</p>
      <div className="prose-block text-base leading-relaxed sm:text-lg">{children}</div>
    </aside>
  );
}

/** KaTeX rendered at build time; only the stylesheet reaches the browser. */
export function FormulaBlock({ tex, label }: { tex: string; label: string }) {
  const html = katex.renderToString(tex, { displayMode: true, throwOnError: true, output: "htmlAndMathml" });
  return (
    <div
      role="math"
      aria-label={label}
      className="card overflow-x-auto px-4 py-5 text-[0.95rem] sm:text-base"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function InlineMath({ tex }: { tex: string }) {
  const html = katex.renderToString(tex, { throwOnError: true });
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

export function DataTable({ head, rows, caption }: { head: ReactNode[]; rows: ReactNode[][]; caption?: string }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[420px] text-left text-sm">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wider text-muted">
            {head.map((h, i) => (
              <th key={i} scope="col" className="px-4 py-3 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-line/60 last:border-0">
              {row.map((cell, k) =>
                k === 0 ? (
                  <th key={k} scope="row" className="px-4 py-2.5 font-medium">
                    {cell}
                  </th>
                ) : (
                  <td key={k} className="num px-4 py-2.5">
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
