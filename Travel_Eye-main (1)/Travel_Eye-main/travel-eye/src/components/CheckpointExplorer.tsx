"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { StoryModal } from "@/components/StoryModal";
import { referenceSources } from "@/lib/checkpoints";
import { DISCOVERIES_EVENT, DISCOVERIES_STORAGE_KEY, discoveriesFromRaw } from "@/lib/discoveries";
import { CATEGORY_LABEL } from "@/lib/labels";
import { useBrowserStorage } from "@/lib/use-browser-storage";
import type { Checkpoint, Site } from "@/types";

export function CheckpointExplorer({
  site,
  variant,
}: {
  site: Site;
  variant: "index" | "reader";
}) {
  const discoveriesRaw = useBrowserStorage(DISCOVERIES_STORAGE_KEY, DISCOVERIES_EVENT);
  const discoveredIds = useMemo(() => {
    const entries = discoveriesFromRaw(discoveriesRaw)[site.slug] ?? [];
    return new Set(entries.map((item) => item.checkpointId));
  }, [discoveriesRaw, site.slug]);
  const [selected, setSelected] = useState<Checkpoint | null>(null);

  useEffect(() => {
    if (variant !== "reader") return;
    const id = window.location.hash.replace("#", "");
    if (!id) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById(id)?.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      block: "start",
    });
  }, [variant]);

  return (
    <>
      <ol className={variant === "reader" ? "divide-y divide-line" : ""}>
        {site.checkpoints.map((checkpoint) => {
          const found = discoveredIds.has(checkpoint.id);
          const status = found ? "Found" : "Not yet found";
          const anchor = `checkpoint-${checkpoint.id}`;

          if (variant === "index") {
            return (
              <li key={checkpoint.id}>
                <Link
                  href={`/explore/${site.slug}/checkpoints#${anchor}`}
                  className="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-4 gap-y-1 border-b border-line py-5 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
                  aria-label={`${checkpoint.name}, ${status}`}
                >
                  <span className="text-xs tracking-[0.16em] text-accent">
                    {String(checkpoint.sortOrder).padStart(2, "0")}
                  </span>
                  <span>
                    <span className="block font-display text-2xl leading-tight text-primary md:text-3xl">
                      {checkpoint.name}
                    </span>
                    <span className="mt-1 block text-sm text-muted">
                      {CATEGORY_LABEL[checkpoint.category]}
                      <span className="sm:hidden"> · {status}</span>
                    </span>
                  </span>
                  <span className="hidden text-sm text-muted sm:block">{status}</span>
                </Link>
              </li>
            );
          }

          return (
            <li key={checkpoint.id} id={anchor} className="scroll-mt-28 py-10">
              <div className="grid gap-6 md:grid-cols-[8rem_1fr]">
                <p className="font-display text-4xl text-gold">{String(checkpoint.sortOrder).padStart(2, "0")}</p>
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-accent">
                    {CATEGORY_LABEL[checkpoint.category]}
                  </p>
                  <h2 className="mt-2 font-display text-3xl leading-tight text-primary md:text-4xl">
                    {checkpoint.name}
                  </h2>
                  <p className="mt-2 text-sm text-muted">{status}</p>
                  <p className="mt-4 max-w-prose text-base leading-relaxed">{checkpoint.shortDescription}</p>
                  {referenceSources(checkpoint).length === 0 && (
                    <p className="mt-3 max-w-prose text-sm text-muted">
                      No reference photograph is on record, so the scanner cannot match this place yet.
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => setSelected(checkpoint)}
                    className="mt-5 inline-flex min-h-11 items-center border-b border-primary text-sm font-medium text-primary"
                  >
                    Read the story
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
      {selected && <StoryModal checkpoint={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
