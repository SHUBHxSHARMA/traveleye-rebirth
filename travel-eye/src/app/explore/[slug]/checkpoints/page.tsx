import type { Metadata } from "next";
import Link from "next/link";
import { ButtonLink } from "@/components/Button";
import { CheckpointExplorer } from "@/components/CheckpointExplorer";
import { DiscoveryProgress } from "@/components/DiscoveryProgress";
import { MissingSite } from "@/components/MissingSite";
import { getSiteBySlug } from "@/lib/data/sites";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const site = getSiteBySlug(slug);
  return { title: site ? `${site.name} places` : "Places" };
}

export default async function CheckpointsPage({ params }: PageProps) {
  const { slug } = await params;
  const site = getSiteBySlug(slug);
  if (!site) return <MissingSite />;

  return (
    <div className="mx-auto max-w-6xl px-5 py-12 md:px-8 md:py-16">
      <p className="text-xs uppercase tracking-[0.2em] text-accent">
        <Link href={`/explore/${site.slug}`} className="hover:underline">
          {site.city}, {site.country}
        </Link>
      </p>
      <div className="mt-4 flex flex-col justify-between gap-6 md:flex-row md:items-end">
        <div>
          <h1 className="font-display text-5xl leading-tight text-primary md:text-6xl">Places at {site.name}</h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed">
            Read a history before you walk to it. Found places are remembered on this device.
          </p>
        </div>
        <ButtonLink href={`/explore/${site.slug}/lens`} className="w-full sm:w-auto">
          Return to scanner
        </ButtonLink>
      </div>
      <div className="mt-10 max-w-xl">
        <DiscoveryProgress site={site} />
      </div>
      <div className="mt-6">
        <CheckpointExplorer site={site} variant="reader" />
      </div>
    </div>
  );
}
