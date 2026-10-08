import Link from "next/link";
import { meta, repoUrl } from "@/lib/data";
import { Badge } from "./ui";

export function SiteFooter() {
  const date = meta.generated_at.slice(0, 10);
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <p className="text-text">GreenWave-RL</p>
          <p>Course project: Artificial Intelligence, B.Tech Computer Engineering, 3rd year.</p>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {meta.synthetic_demand ? <Badge tone="amber">Data: synthetic demand</Badge> : null}
          {meta.mock ? <Badge tone="amber">Preview data</Badge> : null}
          <span className="num">
            build {meta.git_sha.slice(0, 7)} · {date} · profile {meta.profile}
          </span>
          <Link href={repoUrl} className="text-text underline decoration-line underline-offset-4 hover:decoration-wave-b">
            GitHub
          </Link>
        </div>
      </div>
    </footer>
  );
}
