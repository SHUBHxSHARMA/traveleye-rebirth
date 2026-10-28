import type { Metadata } from "next";
import { DestinationSearch } from "@/components/DestinationSearch";

export const metadata: Metadata = {
  title: "Destinations",
  description: "Browse the historic places currently in the Travel Eye guide.",
};

export default function DestinationsPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-14 md:px-8 md:py-20">
      <p className="text-xs uppercase tracking-[0.2em] text-accent">The guide</p>
      <h1 className="mt-3 max-w-3xl font-display text-5xl leading-tight text-primary md:text-6xl">
        Places with a record you can stand in front of.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-relaxed">
        Search by name or city. Each destination opens its history, its places, and the scanner.
      </p>
      <div className="mt-12">
        <DestinationSearch variant="browse" />
      </div>
    </div>
  );
}
