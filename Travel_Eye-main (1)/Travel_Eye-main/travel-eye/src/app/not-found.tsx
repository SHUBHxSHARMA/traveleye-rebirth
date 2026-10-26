import Link from "next/link";
import { ButtonLink } from "@/components/Button";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-5 py-28">
      <p className="text-xs uppercase tracking-[0.2em] text-accent">Missing page</p>
      <h1 className="mt-3 font-display text-5xl leading-tight text-primary">This page is not on the route.</h1>
      <p className="mt-4 text-muted">The address may be incomplete, or the place is not in the guide yet.</p>
      <div className="mt-8 flex gap-4">
        <ButtonLink href="/">Home</ButtonLink>
        <Link href="/destinations" className="inline-flex min-h-11 items-center text-sm text-primary underline-offset-4 hover:underline">
          Destinations
        </Link>
      </div>
    </div>
  );
}
