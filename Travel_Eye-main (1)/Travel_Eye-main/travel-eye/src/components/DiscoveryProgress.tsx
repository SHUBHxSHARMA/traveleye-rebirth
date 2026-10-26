"use client";

import { useMemo } from "react";
import { ProgressRing } from "@/components/ProgressRing";
import { DISCOVERIES_EVENT, DISCOVERIES_STORAGE_KEY, discoveriesFromRaw } from "@/lib/discoveries";
import { useBrowserStorage } from "@/lib/use-browser-storage";
import type { Site } from "@/types";

export function DiscoveryProgress({ site }: { site: Site }) {
  const discoveriesRaw = useBrowserStorage(DISCOVERIES_STORAGE_KEY, DISCOVERIES_EVENT);
  const discovered = useMemo(() => {
    return (discoveriesFromRaw(discoveriesRaw)[site.slug] ?? []).length;
  }, [discoveriesRaw, site.slug]);
  const total = site.checkpoints.length;
  const remaining = Math.max(total - discovered, 0);

  return (
    <div className="flex items-center gap-5 border border-line bg-surface px-5 py-5">
      <ProgressRing discovered={discovered} total={total} />
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-accent">Progress on this device</p>
        <p className="mt-2 font-display text-2xl leading-tight text-primary">
          {discovered} of {total} found
        </p>
        <p className="mt-1 text-sm text-muted">
          {remaining === 0
            ? "Every marked place at this site has been found."
            : `${remaining} still to find.`}
        </p>
      </div>
    </div>
  );
}
