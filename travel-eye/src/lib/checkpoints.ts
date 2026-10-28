import type { Checkpoint, ImageCredit, Site } from "@/types";

export type PositionedCheckpoint = Checkpoint & {
  latitude: number;
  longitude: number;
  radiusMeters: number;
};

export function referenceSources(checkpoint: Checkpoint): string[] {
  const urls = [
    ...(checkpoint.referenceImageUrls ?? []),
    ...(checkpoint.referenceImageUrl ? [checkpoint.referenceImageUrl] : []),
  ];
  return [...new Set(urls.filter((url) => url.length > 0))];
}

export function positionedCheckpoints(checkpoints: Checkpoint[]): PositionedCheckpoint[] {
  return checkpoints.filter(
    (checkpoint): checkpoint is PositionedCheckpoint =>
      typeof checkpoint.latitude === "number" &&
      typeof checkpoint.longitude === "number" &&
      typeof checkpoint.radiusMeters === "number",
  );
}

export function siteImageCredits(site: Site): ImageCredit[] {
  const credits = [site.coverCredit, ...site.checkpoints.map((checkpoint) => checkpoint.imageCredit)];
  const seen = new Set<string>();
  return credits.filter((credit): credit is ImageCredit => {
    if (!credit) return false;
    const key = `${credit.author}|${credit.license}|${credit.source}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
