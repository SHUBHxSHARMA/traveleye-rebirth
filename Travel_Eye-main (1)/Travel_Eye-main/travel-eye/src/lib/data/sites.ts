import { KHAJURAHO } from "@/lib/data/khajuraho";
import { QUTUB_MINAR } from "@/lib/data/qutub-minar";
import { RED_FORT } from "@/lib/data/red-fort";
import { SANCHI_STUPA } from "@/lib/data/sanchi";
import { TAJ_MAHAL } from "@/lib/data/taj-mahal";
import type { Checkpoint, Site } from "@/types";

export const SITES: Site[] = [RED_FORT, TAJ_MAHAL, QUTUB_MINAR, SANCHI_STUPA, KHAJURAHO];

export function getSiteBySlug(slug: string): Site | undefined {
  return SITES.find((site) => site.slug === slug);
}

export function getCheckpointById(site: Site, checkpointId: string): Checkpoint | undefined {
  return site.checkpoints.find((checkpoint) => checkpoint.id === checkpointId);
}
