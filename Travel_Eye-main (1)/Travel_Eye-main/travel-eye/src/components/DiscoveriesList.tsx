"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ButtonLink } from "@/components/Button";
import { StoryModal } from "@/components/StoryModal";
import { DISCOVERIES_EVENT, DISCOVERIES_STORAGE_KEY, discoveriesFromRaw } from "@/lib/discoveries";
import { getSiteBySlug } from "@/lib/data/sites";
import { METHOD_LABEL } from "@/lib/labels";
import { useBrowserStorage } from "@/lib/use-browser-storage";
import type { Checkpoint, Discovery } from "@/types";

interface Row {
  siteSlug: string;
  siteName: string;
  discovery: Discovery;
  checkpoint: Checkpoint;
}

export function DiscoveriesList() {
  const raw = useBrowserStorage(DISCOVERIES_STORAGE_KEY, DISCOVERIES_EVENT);
  const [selected, setSelected] = useState<Checkpoint | null>(null);
  const rows = useMemo(() => {
    const next: Row[] = [];
    for (const [slug, discoveries] of Object.entries(discoveriesFromRaw(raw))) {
      const site = getSiteBySlug(slug);
      if (!site) continue;
      for (const discovery of discoveries) {
        const checkpoint = site.checkpoints.find((item) => item.id === discovery.checkpointId);
        if (!checkpoint) continue;
        next.push({ siteSlug: slug, siteName: site.name, discovery, checkpoint });
      }
    }
    next.sort((a, b) => b.discovery.discoveredAt.localeCompare(a.discovery.discoveredAt));
    return next;
  }, [raw]);

  if (rows.length === 0) {
    return (
      <div className="max-w-xl border-t border-line py-10">
        <h2 className="font-display text-3xl text-primary">Nothing saved yet.</h2>
        <p className="mt-3 leading-relaxed text-muted">
          When a landmark matches a photograph, or you come within range of a checkpoint, it is kept in this browser.
        </p>
        <ButtonLink href="/destinations" className="mt-8">
          Browse destinations
        </ButtonLink>
      </div>
    );
  }

  return (
    <>
      <ul className="divide-y divide-line border-y border-line">
        {rows.map((row) => {
          const date = new Date(row.discovery.discoveredAt);
          const dateLabel = Number.isNaN(date.getTime())
            ? ""
            : date.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
          return (
            <li key={`${row.siteSlug}-${row.checkpoint.id}`} className="grid gap-4 py-7 md:grid-cols-[1fr_auto] md:items-center">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-accent">{row.siteName}</p>
                <h2 className="mt-2 font-display text-3xl text-primary">{row.checkpoint.name}</h2>
                <p className="mt-2 text-sm text-muted">
                  {METHOD_LABEL[row.discovery.method]}
                  {dateLabel ? ` · ${dateLabel}` : ""}
                </p>
                <p className="mt-3 max-w-prose text-sm leading-relaxed">{row.checkpoint.shortDescription}</p>
              </div>
              <div className="flex flex-col items-start gap-2">
                <button
                  type="button"
                  onClick={() => setSelected(row.checkpoint)}
                  className="inline-flex min-h-11 items-center border-b border-primary text-sm font-medium text-primary"
                >
                  Read the story
                </button>
                <Link
                  href={`/explore/${row.siteSlug}/checkpoints#checkpoint-${row.checkpoint.id}`}
                  className="inline-flex min-h-11 items-center text-sm text-muted hover:text-primary"
                >
                  View at the destination
                </Link>
              </div>
            </li>
          );
        })}
      </ul>
      {selected && <StoryModal checkpoint={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
