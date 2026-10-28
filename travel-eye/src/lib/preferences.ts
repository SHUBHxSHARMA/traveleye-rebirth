export const NARRATION_LANGUAGES = [{ code: "en-IN", label: "English" }] as const;

export type NarrationLanguage = (typeof NARRATION_LANGUAGES)[number];

export const NARRATION_STORAGE_KEY = "travel-eye-narration-lang";
export const NARRATION_EVENT = "travel-eye-narration";

const STORAGE_KEY = NARRATION_STORAGE_KEY;

export function getNarrationLanguage(): NarrationLanguage {
  const fallback = NARRATION_LANGUAGES[0];
  if (typeof window === "undefined") return fallback;
  const stored = localStorage.getItem(STORAGE_KEY);
  return NARRATION_LANGUAGES.find((language) => language.code === stored) ?? fallback;
}

export function setNarrationLanguage(code: string): NarrationLanguage {
  const match =
    NARRATION_LANGUAGES.find((language) => language.code === code) ??
    NARRATION_LANGUAGES[0];
  localStorage.setItem(STORAGE_KEY, match.code);
  window.dispatchEvent(new Event(NARRATION_EVENT));
  return match;
}
