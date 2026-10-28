"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/Wordmark";

const LINKS = [
  { href: "/destinations", label: "Destinations" },
  { href: "/discoveries", label: "Saved discoveries" },
  { href: "/settings", label: "Settings" },
  { href: "/start", label: "Begin" },
];

export function SiteFooter() {
  const pathname = usePathname();
  if (pathname.includes("/lens")) return null;

  return (
    <footer className="mt-auto border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 md:grid-cols-[1.4fr_1fr] md:px-8">
        <div>
          <Link href="/" aria-label="Travel Eye home">
            <Wordmark />
          </Link>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted">
            A camera companion for historic places. Point, identify, and read the record of what is in front of you.
          </p>
        </div>
        <nav aria-label="Footer">
          <ul className="grid gap-2 text-sm">
            {LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="inline-flex min-h-11 items-center hover:text-primary">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="border-t border-line pb-[env(safe-area-inset-bottom)]">
        <p className="mx-auto max-w-6xl px-5 py-4 text-xs tracking-wide text-muted md:px-8">
          Destinations on record: Red Fort, Taj Mahal, Qutub Minar, Sanchi Stupa, and Khajuraho.
        </p>
      </div>
    </footer>
  );
}
