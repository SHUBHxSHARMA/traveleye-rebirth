export const EXPLORER_STORAGE_KEY = "travel-eye-explorer";
export const EXPLORER_EVENT = "travel-eye-profile";

const EXPLORER_KEY = EXPLORER_STORAGE_KEY;

export function getExplorerName(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(EXPLORER_KEY);
}

export function setExplorerName(name: string): void {
  localStorage.setItem(EXPLORER_KEY, name.trim());
  window.dispatchEvent(new Event(EXPLORER_EVENT));
}

export function clearExplorerName(): void {
  localStorage.removeItem(EXPLORER_KEY);
  window.dispatchEvent(new Event(EXPLORER_EVENT));
}
