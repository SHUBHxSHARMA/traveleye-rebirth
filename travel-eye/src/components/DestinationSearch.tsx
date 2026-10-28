"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { SITES } from "@/lib/data/sites";
import type { Site } from "@/types";

function matches(site: Site, query: string) {
  const haystack = `${site.name} ${site.city} ${site.country} ${site.description}`.toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}

export function DestinationSearch({ variant }: { variant: "home" | "browse" }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const results = useMemo(
    () => SITES.filter((site) => matches(site, query)),
    [query],
  );
  const showResults = variant === "browse" || query.trim().length > 0;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (results.length === 1) {
      router.push(`/explore/${results[0].slug}`);
    }
  }

  return (
    <div>
      <form role="search" onSubmit={onSubmit} className="border-b border-line">
        <label htmlFor={`${variant}-destination-query`} className="text-xs uppercase tracking-[0.18em] text-accent">
          Search destinations
        </label>
        <input
          id={`${variant}-destination-query`}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try Taj Mahal, Sanchi, or Delhi"
          className="mt-1 min-h-12 w-full bg-transparent py-3 text-xl text-foreground outline-none placeholder:text-[#b3aa9d] md:text-3xl"
        />
      </form>

      {showResults && results.length === 0 && (
        <p className="py-8 text-base text-muted" role="status">
          No destination matches “{query.trim()}”. The guide includes the Red Fort, the Taj Mahal, Qutub Minar, Sanchi Stupa, and Khajuraho.
        </p>
      )}

      {showResults && results.length > 0 && variant === "home" && (
        <ul className="divide-y divide-line border-b border-line" aria-label="Matching destinations">
          {results.map((site) => (
            <li key={site.id}>
              <Link
                href={`/explore/${site.slug}`}
                className="flex min-h-20 items-center gap-4 py-3 hover:text-primary"
              >
                <span className="relative h-14 w-20 shrink-0 overflow-hidden bg-line">
                  <Image
                    src={site.coverImage}
                    alt=""
                    fill
                    className="object-cover"
                    sizes="80px"
                  />
                </span>
                <span>
                  <span className="block font-display text-2xl leading-tight">{site.name}</span>
                  <span className="text-sm text-muted">
                    {site.city}, {site.country}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {variant === "browse" && results.length > 0 && (
        <ul className="mt-10 flex flex-col gap-16" aria-label="Destinations">
          {results.map((site, index) => (
            <li key={site.id}>
              <article className="grid items-stretch gap-6 md:grid-cols-12 md:gap-10">
                <Link
                  href={`/explore/${site.slug}`}
                  className={`group relative block min-h-72 overflow-hidden bg-line md:col-span-7 ${
                    index % 2 === 1 ? "md:order-2" : ""
                  }`}
                >
                  <Image
                    src={site.coverImage}
                    alt={site.coverAlt ?? `${site.name} in ${site.city}`}
                    fill
                    className="object-cover transition-transform duration-700 motion-reduce:transition-none motion-safe:group-hover:scale-[1.03]"
                    sizes="(min-width: 768px) 58vw, 100vw"
                  />
                </Link>
                <div className={`flex flex-col justify-center md:col-span-5 ${index % 2 === 1 ? "md:order-1" : ""}`}>
                  <p className="text-xs uppercase tracking-[0.18em] text-accent">
                    {site.city}, {site.country}
                  </p>
                  <h2 className="mt-3 font-display text-4xl leading-tight text-primary md:text-5xl">
                    <Link href={`/explore/${site.slug}`} className="hover:underline">
                      {site.name}
                    </Link>
                  </h2>
                  <p className="mt-4 max-w-prose text-base leading-relaxed text-foreground">{site.description}</p>
                  <p className="mt-4 text-sm text-muted">
                    {site.checkpoints.length} places to find
                  </p>
                  <Link
                    href={`/explore/${site.slug}`}
                    className="mt-6 inline-flex min-h-11 items-center self-start border-b border-primary text-sm font-medium text-primary"
                  >
                    Explore destination
                  </Link>
                </div>
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
