"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { Button } from "@/components/Button";
import { clearLocalDiscoveries } from "@/lib/discoveries";
import { EXPLORER_EVENT, EXPLORER_STORAGE_KEY, setExplorerName } from "@/lib/explorer";
import { getSiteBySlug } from "@/lib/data/sites";
import {
  getNarrationLanguage,
  NARRATION_EVENT,
  NARRATION_LANGUAGES,
  NARRATION_STORAGE_KEY,
  setNarrationLanguage,
} from "@/lib/preferences";
import { getSavedSiteSlugs, SAVED_SITES_EVENT, SAVED_SITES_STORAGE_KEY, setSiteSaved } from "@/lib/saved-sites";
import { useBrowserStorage } from "@/lib/use-browser-storage";

export function SettingsPanel() {
  const storedName = useBrowserStorage(EXPLORER_STORAGE_KEY, EXPLORER_EVENT);
  const narrationRaw = useBrowserStorage(NARRATION_STORAGE_KEY, NARRATION_EVENT);
  const savedRaw = useBrowserStorage(SAVED_SITES_STORAGE_KEY, SAVED_SITES_EVENT);
  const [draft, setDraft] = useState<string | null>(null);
  const [nameNote, setNameNote] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);
  const [cleared, setCleared] = useState(false);
  const name = draft ?? storedName;
  const language = narrationRaw || getNarrationLanguage().code;

  const savedSites = useMemo(() => {
    if (!savedRaw) return [];
    return getSavedSiteSlugs()
      .map((slug) => getSiteBySlug(slug))
      .filter((site): site is NonNullable<typeof site> => Boolean(site));
  }, [savedRaw]);

  function saveName(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameNote("Enter a name, or continue as a guest from the begin screen.");
      return;
    }
    setExplorerName(trimmed);
    setDraft(null);
    setNameNote("Name saved on this device.");
  }

  return (
    <div className="max-w-2xl divide-y divide-line border-y border-line">
      <form onSubmit={saveName} className="py-8">
        <h2 className="font-display text-3xl text-primary">Your name</h2>
        <p className="mt-2 text-sm text-muted">Shown in the header. It is not sent to an account.</p>
        <label htmlFor="settings-name" className="mt-5 block text-sm font-medium">
          Explorer name
        </label>
        <input
          id="settings-name"
          value={name}
          maxLength={30}
          onChange={(event) => setDraft(event.target.value)}
          className="mt-2 w-full border-b border-line bg-transparent py-3 text-base outline-none"
        />
        <Button type="submit" className="mt-6 w-full sm:w-auto">
          Save name
        </Button>
        {nameNote && (
          <p className="mt-3 text-sm text-muted" role="status">
            {nameNote}
          </p>
        )}
      </form>

      <fieldset className="py-8">
        <legend className="font-display text-3xl text-primary">Narration language</legend>
        <p className="mt-2 max-w-prose text-sm leading-relaxed text-muted">
          Stories in the guide are written in English. Listening uses your device voice for the language selected here. Translations are not available yet.
        </p>
        <div className="mt-5 grid gap-3">
          {NARRATION_LANGUAGES.map((item) => (
            <label key={item.code} className="flex min-h-11 items-center gap-3 text-sm">
              <input
                type="radio"
                name="narration-language"
                value={item.code}
                checked={language === item.code}
                onChange={() => setNarrationLanguage(item.code)}
              />
              {item.label}
            </label>
          ))}
        </div>
      </fieldset>

      <section className="py-8">
        <h2 className="font-display text-3xl text-primary">Saved destinations</h2>
        {savedSites.length === 0 ? (
          <p className="mt-3 text-sm text-muted">You have not saved a destination yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-line">
            {savedSites.map((site) => (
              <li key={site.slug} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <Link href={`/explore/${site.slug}`} className="inline-flex min-h-11 min-w-0 flex-col justify-center hover:underline">
                  <span className="block font-medium">{site.name}</span>
                  <span className="text-sm text-muted">
                    {site.city}, {site.country}
                  </span>
                </Link>
                <button
                  type="button"
                  onClick={() => setSiteSaved(site.slug, false)}
                  className="inline-flex min-h-11 items-center text-sm text-primary underline-offset-4 hover:underline"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="py-8">
        <h2 className="font-display text-3xl text-primary">Exploration progress</h2>
        <p className="mt-2 max-w-prose text-sm leading-relaxed text-muted">
          Clearing removes the checkpoints marked as found on this device. Your name and saved destinations stay.
        </p>
        <Link href="/discoveries" className="mt-4 inline-flex min-h-11 items-center text-sm text-primary underline-offset-4 hover:underline">
          Review saved discoveries
        </Link>
        {!confirmClear ? (
          <div>
            <Button type="button" variant="secondary" className="mt-4 w-full sm:w-auto" onClick={() => setConfirmClear(true)}>
              Clear progress
            </Button>
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <Button
              type="button"
              className="w-full sm:w-auto"
              onClick={() => {
                clearLocalDiscoveries();
                setConfirmClear(false);
                setCleared(true);
              }}
            >
              Confirm clear
            </Button>
            <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={() => setConfirmClear(false)}>
              Cancel
            </Button>
          </div>
        )}
        {cleared && (
          <p className="mt-3 text-sm text-muted" role="status">
            Progress cleared on this device.
          </p>
        )}
      </section>
    </div>
  );
}
