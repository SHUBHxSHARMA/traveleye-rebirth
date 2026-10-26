"use client";

import { Volume2, VolumeX, X } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef } from "react";
import { useStoryAudio } from "@/components/useStoryAudio";
import { CATEGORY_LABEL } from "@/lib/labels";
import type { Checkpoint } from "@/types";

interface StoryModalProps {
  checkpoint: Checkpoint;
  onClose: () => void;
}

export function StoryModal({ checkpoint, onClose }: StoryModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const spokenText = `${checkpoint.name}. ${checkpoint.story}`;
  const { speaking, unsupported, toggle } = useStoryAudio(spokenText);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center overscroll-contain bg-[#1c1915]/55 sm:items-center sm:p-6">
      <button
        type="button"
        aria-label="Close story"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="story-title"
        tabIndex={-1}
        className="relative flex max-h-[92dvh] w-full max-w-2xl flex-col overflow-hidden bg-surface pb-[env(safe-area-inset-bottom)] shadow-[0_24px_60px_rgba(20,48,40,0.18)]"
      >
        <div className="relative h-40 shrink-0 bg-line sm:h-64">
          {checkpoint.referenceImageUrl ? (
            <Image
              src={checkpoint.referenceImageUrl}
              alt={checkpoint.name}
              fill
              className="object-cover"
              sizes="(min-width: 768px) 42rem, 100vw"
            />
          ) : (
            <div className="flex h-full items-end px-5 py-4">
              <p className="text-sm text-muted">No reference photograph is on record for this place.</p>
            </div>
          )}
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 inline-flex min-h-11 min-w-11 items-center justify-center bg-ivory text-primary"
            aria-label="Close story"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <div className="overflow-y-auto overscroll-contain px-5 py-6 sm:px-8 sm:py-8">
          <p className="text-xs uppercase tracking-[0.18em] text-accent">
            {CATEGORY_LABEL[checkpoint.category]}
          </p>
          <h2 id="story-title" className="mt-2 font-display text-4xl leading-tight text-primary">
            {checkpoint.name}
          </h2>
          <p className="mt-3 text-base text-muted">{checkpoint.shortDescription}</p>
          <p className="mt-6 font-display text-xl font-normal leading-relaxed text-foreground">
            {checkpoint.story}
          </p>
          {unsupported && (
            <p className="mt-4 text-sm text-muted" role="status">
              Listening is not available in this browser. You can still read the story.
            </p>
          )}
          <button
            type="button"
            onClick={toggle}
            aria-pressed={speaking}
            className="mt-8 inline-flex min-h-11 w-full items-center justify-center gap-2 bg-primary px-5 text-sm font-medium text-ivory hover:bg-primary-dark sm:w-auto"
          >
            {speaking ? <VolumeX className="h-4 w-4" aria-hidden="true" /> : <Volume2 className="h-4 w-4" aria-hidden="true" />}
            {speaking ? "Stop reading" : "Listen to the story"}
          </button>
        </div>
      </div>
    </div>
  );
}
