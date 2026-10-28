"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/Button";
import { EXPLORER_EVENT, EXPLORER_STORAGE_KEY, setExplorerName } from "@/lib/explorer";
import { RED_FORT } from "@/lib/data/red-fort";
import { useBrowserStorage } from "@/lib/use-browser-storage";

export function StartForm() {
  const router = useRouter();
  const storedName = useBrowserStorage(EXPLORER_STORAGE_KEY, EXPLORER_EVENT);
  const [draft, setDraft] = useState<string | null>(null);
  const name = draft ?? storedName;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setExplorerName(name);
    router.push("/destinations");
  }

  function handleSkip() {
    setExplorerName("Explorer");
    router.push("/destinations");
  }

  return (
    <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-14 md:grid-cols-2 md:px-8 md:py-24">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-accent">Begin</p>
        <h1 className="mt-3 font-display text-5xl leading-tight text-primary md:text-6xl">
          What should we call you?
        </h1>
        <p className="mt-5 max-w-md text-lg leading-relaxed">
          No account is required. The name stays on this device and appears beside your progress.
        </p>
        <form onSubmit={handleSubmit} className="mt-10 max-w-md">
          <label htmlFor="explorer-name" className="text-sm font-medium">
            Explorer name
          </label>
          <input
            id="explorer-name"
            type="text"
            required
            maxLength={30}
            value={name}
            placeholder="For example, Rahul"
            onChange={(event) => setDraft(event.target.value)}
            className="mt-2 w-full border-b border-line bg-transparent py-3 text-base outline-none"
          />
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button type="submit" className="w-full sm:w-auto">
              Continue
            </Button>
            <Button type="button" variant="secondary" onClick={handleSkip} className="w-full sm:w-auto">
              Continue as guest
            </Button>
          </div>
        </form>
        <p className="mt-8 text-sm text-muted">
          Already exploring?{" "}
          <Link href={`/explore/${RED_FORT.slug}`} className="text-primary underline-offset-4 hover:underline">
            Return to {RED_FORT.name}
          </Link>
        </p>
      </div>
      <div className="relative min-h-80">
        <Image
          src={RED_FORT.coverImage}
          alt="Lahori Gate of the Red Fort in Delhi"
          fill
          className="object-cover"
          sizes="(min-width: 768px) 50vw, 100vw"
        />
      </div>
    </div>
  );
}
