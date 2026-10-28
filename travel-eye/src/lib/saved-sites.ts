export const SAVED_SITES_STORAGE_KEY = "travel-eye-saved-sites";
export const SAVED_SITES_EVENT = "travel-eye-saved-sites";

const STORAGE_KEY = SAVED_SITES_STORAGE_KEY;

function read(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is string => typeof value === "string");
  } catch {
    return [];
  }
}

function write(slugs: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(slugs));
  window.dispatchEvent(new Event(SAVED_SITES_EVENT));
}

export function getSavedSiteSlugs(): string[] {
  return read();
}

export function isSiteSaved(slug: string): boolean {
  return read().includes(slug);
}

export function setSiteSaved(slug: string, saved: boolean): string[] {
  const current = read();
  const next = saved
    ? Array.from(new Set([...current, slug]))
    : current.filter((item) => item !== slug);
  write(next);
  return next;
}
