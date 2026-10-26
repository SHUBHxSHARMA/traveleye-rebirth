import type { Metadata } from "next";
import { DiscoveriesList } from "@/components/DiscoveriesList";

export const metadata: Metadata = {
  title: "Saved discoveries",
  description: "Checkpoints found on this device.",
};

export default function DiscoveriesPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-14 md:px-8 md:py-20">
      <p className="text-xs uppercase tracking-[0.2em] text-accent">On this device</p>
      <h1 className="mt-3 font-display text-5xl leading-tight text-primary md:text-6xl">Saved discoveries</h1>
      <p className="mt-4 max-w-xl text-lg leading-relaxed">
        Places you have matched or come near, kept in this browser.
      </p>
      <div className="mt-12">
        <DiscoveriesList />
      </div>
    </div>
  );
}
