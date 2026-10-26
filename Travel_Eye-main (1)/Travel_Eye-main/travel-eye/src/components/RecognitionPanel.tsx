"use client";

import { Volume2, VolumeX } from "lucide-react";
import Link from "next/link";
import type { Checkpoint } from "@/types";

interface RecognitionPanelProps {
  checkpoint: Checkpoint | null;
  message: string | null;
  heading?: string;
  saved: boolean;
  speaking: boolean;
  audioNote: string | null;
  onListen: () => void;
  onOpenStory: () => void;
  onSave: () => void;
  onScanAgain: () => void;
  checkpointsHref: string;
}

export function RecognitionPanel({
  checkpoint,
  message,
  heading = "No reliable match found",
  saved,
  speaking,
  audioNote,
  onListen,
  onOpenStory,
  onSave,
  onScanAgain,
  checkpointsHref,
}: RecognitionPanelProps) {
  return (
    <section className="border-t border-[#d9d0c2] bg-background px-5 py-6 text-foreground" aria-live="polite">
      {checkpoint ? (
        <>
          <p className="text-xs uppercase tracking-[0.18em] text-accent">Recognized landmark</p>
          <h2 className="mt-2 font-display text-4xl leading-tight text-primary">{checkpoint.name}</h2>
          <p className="mt-3 text-sm text-muted">
            This photograph is close to a reference image kept for this place.
          </p>
          <p className="mt-5 max-w-prose text-base leading-relaxed">{checkpoint.shortDescription}</p>
          <p className="mt-4 max-w-prose font-display text-lg font-normal leading-relaxed">{checkpoint.story}</p>
          {audioNote && (
            <p className="mt-4 text-sm text-muted" role="status">
              {audioNote}
            </p>
          )}
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <button
              type="button"
              onClick={onListen}
              aria-pressed={speaking}
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 bg-primary px-5 text-sm font-medium text-ivory sm:w-auto"
            >
              {speaking ? <VolumeX className="h-4 w-4" aria-hidden="true" /> : <Volume2 className="h-4 w-4" aria-hidden="true" />}
              {speaking ? "Stop reading" : "Listen"}
            </button>
            <button
              type="button"
              onClick={onOpenStory}
              className="inline-flex min-h-11 w-full items-center justify-center border border-primary px-5 text-sm font-medium text-primary sm:w-auto"
            >
              Read the story
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={saved}
              aria-pressed={saved}
              className="inline-flex min-h-11 w-full items-center justify-center border border-primary px-5 text-sm font-medium text-primary disabled:opacity-70 sm:w-auto"
            >
              {saved ? "Saved on this device" : "Save discovery"}
            </button>
            <button
              type="button"
              onClick={onScanAgain}
              className="inline-flex min-h-11 w-full items-center justify-center px-5 text-sm font-medium text-primary underline-offset-4 hover:underline sm:w-auto"
            >
              Scan again
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-xs uppercase tracking-[0.18em] text-accent">Scan result</p>
          <h2 className="mt-2 font-display text-3xl leading-tight text-primary">{heading}</h2>
          <p className="mt-4 max-w-prose text-base leading-relaxed">
            {message ?? "No reliable match found. Try a clearer photograph of one place, or choose it from the list."}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={onScanAgain}
              className="inline-flex min-h-11 w-full items-center justify-center bg-primary px-5 text-sm font-medium text-ivory sm:w-auto"
            >
              Scan again
            </button>
            <Link
              href={checkpointsHref}
              className="inline-flex min-h-11 w-full items-center justify-center border border-primary px-5 text-sm font-medium text-primary sm:w-auto"
            >
              Choose a place
            </Link>
          </div>
        </>
      )}
    </section>
  );
}
