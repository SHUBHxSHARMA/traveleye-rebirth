"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Wordmark } from "@/components/Wordmark";
import { EXPLORER_EVENT, EXPLORER_STORAGE_KEY } from "@/lib/explorer";
import { useBrowserStorage } from "@/lib/use-browser-storage";

const LINKS = [
  { href: "/destinations", label: "Destinations" },
  { href: "/discoveries", label: "Saved" },
  { href: "/settings", label: "Settings" },
];

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const explorerName = useBrowserStorage(EXPLORER_STORAGE_KEY, EXPLORER_EVENT);
  const [menuPath, setMenuPath] = useState(pathname);
  if (menuPath !== pathname) {
    setMenuPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (pathname.includes("/lens")) return null;

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-background pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3.5 md:px-8">
        <Link href="/" aria-label="Travel Eye home">
          <Wordmark />
        </Link>

        <nav className="hidden items-center gap-7 text-sm lg:flex" aria-label="Primary">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`inline-flex min-h-11 items-center underline-offset-4 hover:underline ${
                pathname.startsWith(link.href) ? "text-primary" : "text-foreground"
              }`}
              aria-current={pathname.startsWith(link.href) ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
          {explorerName ? (
            <Link href="/settings" className="inline-flex min-h-11 items-center text-muted hover:text-primary">
              {explorerName}
            </Link>
          ) : (
            <Link
              href="/start"
              className="inline-flex min-h-11 items-center bg-primary px-4 text-sm font-medium text-ivory hover:bg-primary-dark"
            >
              Begin
            </Link>
          )}
        </nav>

        <button
          type="button"
          className="inline-flex min-h-11 min-w-11 items-center justify-center lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-navigation"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
        </button>
      </div>

      {open && (
        <nav
          id="mobile-navigation"
          className="border-t border-line bg-background px-5 py-3 lg:hidden"
          aria-label="Mobile"
        >
          <ul className="flex flex-col">
            {LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="flex min-h-12 items-center text-lg">
                  {link.label}
                </Link>
              </li>
            ))}
            <li>
              <Link href={explorerName ? "/settings" : "/start"} className="flex min-h-12 items-center text-lg">
                {explorerName ? explorerName : "Begin"}
              </Link>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
