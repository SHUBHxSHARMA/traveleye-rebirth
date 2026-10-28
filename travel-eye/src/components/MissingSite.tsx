import Link from "next/link";

export function MissingSite({ tone = "light" }: { tone?: "light" | "dark" }) {
  const dark = tone === "dark";

  return (
    <div
      className={
        dark
          ? "flex min-h-dvh flex-col justify-center bg-[#0c100e] px-6 text-ivory"
          : "mx-auto max-w-xl px-5 py-28"
      }
    >
      <p className={`text-xs uppercase tracking-[0.18em] ${dark ? "text-gold" : "text-accent"}`}>
        Destination
      </p>
      <h1 className="mt-3 font-display text-4xl leading-tight md:text-5xl">
        This place is not in the guide.
      </h1>
      <p className={`mt-4 max-w-md ${dark ? "text-[#d9d3c7]" : "text-muted"}`}>
        Choose one of the destinations in the guide.
      </p>
      <Link
        href="/destinations"
        className={
          dark
            ? "mt-8 inline-flex min-h-11 w-fit items-center bg-ivory px-5 text-sm font-medium text-primary"
            : "mt-8 inline-flex min-h-11 w-fit items-center bg-primary px-5 text-sm font-medium text-ivory hover:bg-primary-dark"
        }
      >
        Browse destinations
      </Link>
    </div>
  );
}
