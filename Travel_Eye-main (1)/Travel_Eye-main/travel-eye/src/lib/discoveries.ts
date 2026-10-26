import type { Discovery, DiscoveryMethod } from "@/types";

export const DISCOVERIES_STORAGE_KEY = "travel-eye-discoveries";
export const DISCOVERIES_EVENT = "travel-eye-discoveries";

const STORAGE_KEY = DISCOVERIES_STORAGE_KEY;

function readAll(): Record<string, Discovery[]> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as Record<
      string,
      Discovery[]
    >;
  } catch {
    return {};
  }
}

function writeAll(data: Record<string, Discovery[]>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  window.dispatchEvent(new Event(DISCOVERIES_EVENT));
}

export function getLocalDiscoveries(siteSlug: string): Discovery[] {
  return readAll()[siteSlug] ?? [];
}

export function addLocalDiscovery(
  siteSlug: string,
  checkpointId: string,
  method: DiscoveryMethod,
): Discovery[] {
  const all = readAll();
  const existing = all[siteSlug] ?? [];
  if (existing.some((d) => d.checkpointId === checkpointId)) {
    return existing;
  }
  const updated = [
    ...existing,
    { checkpointId, method, discoveredAt: new Date().toISOString() },
  ];
  all[siteSlug] = updated;
  writeAll(all);
  return updated;
}

export function isDiscoveredLocally(
  siteSlug: string,
  checkpointId: string,
): boolean {
  return getLocalDiscoveries(siteSlug).some(
    (d) => d.checkpointId === checkpointId,
  );
}

export function getAllLocalDiscoveries(): Record<string, Discovery[]> {
  return readAll();
}

export function discoveriesFromRaw(raw: string): Record<string, Discovery[]> {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as Record<string, Discovery[]>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function clearLocalDiscoveries(siteSlug?: string): void {
  if (typeof window === "undefined") return;
  if (!siteSlug) {
    localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new Event(DISCOVERIES_EVENT));
    return;
  }
  const all = readAll();
  delete all[siteSlug];
  writeAll(all);
}
