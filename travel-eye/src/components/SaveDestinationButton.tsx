"use client";

import { useMemo } from "react";
import { isSiteSaved, SAVED_SITES_EVENT, SAVED_SITES_STORAGE_KEY, setSiteSaved } from "@/lib/saved-sites";
import { useBrowserStorage } from "@/lib/use-browser-storage";

export function SaveDestinationButton({
  slug,
  name,
  className = "",
}: {
  slug: string;
  name: string;
  className?: string;
}) {
  const raw = useBrowserStorage(SAVED_SITES_STORAGE_KEY, SAVED_SITES_EVENT);
  const saved = useMemo(() => {
    if (!raw) return false;
    return isSiteSaved(slug);
  }, [raw, slug]);

  return (
    <button
      type="button"
      aria-pressed={saved}
      aria-label={saved ? `Remove ${name} from saved destinations` : `Save ${name}`}
      onClick={() => setSiteSaved(slug, !saved)}
      className={`inline-flex min-h-11 items-center justify-center border border-primary/80 px-5 text-sm font-medium text-primary hover:bg-primary hover:text-ivory ${className}`}
    >
      {saved ? "Remove from saved" : "Save destination"}
    </button>
  );
}
