"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const NAV = [
  { href: "/demo/", label: "Demo" },
  { href: "/results/", label: "Results" },
  { href: "/method/", label: "Method" },
  { href: "/junction/", label: "Junction" },
  { href: "/about/", label: "About" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/75 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:px-6">
        <Link href="/" aria-label="GreenWave-RL home" className="mr-auto flex shrink-0 items-center">
          <Logo />
        </Link>
        <nav aria-label="Primary" className="-mx-1 overflow-x-auto">
          <ul className="flex items-center gap-0.5 px-1 text-sm">
            {NAV.map((item) => {
              const active = pathname === item.href || pathname === item.href.slice(0, -1);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`relative block rounded-md px-2 py-1.5 transition-colors sm:px-3 ${
                      active ? "text-text" : "text-muted hover:text-text"
                    }`}
                  >
                    {item.label}
                    {active ? (
                      <span
                        aria-hidden
                        className="absolute inset-x-2 -bottom-[9px] h-0.5 rounded-full bg-gradient-to-r from-wave-a to-wave-b sm:inset-x-3"
                      />
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <ThemeToggle />
      </div>
    </header>
  );
}
