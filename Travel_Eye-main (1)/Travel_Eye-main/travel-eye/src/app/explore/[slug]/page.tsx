import Image from "next/image";
import type { Metadata } from "next";
import { ButtonLink } from "@/components/Button";
import { CheckpointExplorer } from "@/components/CheckpointExplorer";
import { DiscoveryProgress } from "@/components/DiscoveryProgress";
import { MissingSite } from "@/components/MissingSite";
import { SaveDestinationButton } from "@/components/SaveDestinationButton";
import { referenceSources, siteImageCredits } from "@/lib/checkpoints";
import { getSiteBySlug } from "@/lib/data/sites";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const site = getSiteBySlug(slug);
  return {
    title: site?.name ?? "Destination",
    description: site?.description,
  };
}

export default async function DestinationPage({ params }: PageProps) {
  const { slug } = await params;
  const site = getSiteBySlug(slug);
  if (!site) return <MissingSite />;
  const credits = siteImageCredits(site);
  const withPhotographs = site.checkpoints.filter((checkpoint) => referenceSources(checkpoint).length > 0).length;

  return (
    <article>
      <div className="relative h-72 bg-line sm:h-96 md:h-[68vh] md:max-h-[46rem] md:min-h-[24rem]">
        <Image
          src={site.coverImage}
          alt={site.coverAlt ?? `${site.name} in ${site.city}`}
          fill
          priority
          className="object-cover object-[center_30%]"
          sizes="100vw"
        />
      </div>
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <header className="relative -mt-16 max-w-3xl bg-background pt-8 md:-mt-24">
          <p className="text-xs uppercase tracking-[0.2em] text-accent">
            {site.city}, {site.country}
          </p>
          <h1 className="mt-3 font-display text-5xl leading-[1.02] text-primary md:text-7xl">{site.name}</h1>
        </header>

        <div className="mt-12 grid gap-12 md:grid-cols-12">
          <div className="md:col-span-7">
            <p className="max-w-prose text-lg leading-relaxed">{site.description}</p>
            <h2 className="mt-8 font-display text-3xl text-primary">Historical overview</h2>
            <p className="mt-4 max-w-prose text-lg leading-relaxed">{site.overview}</p>
            {credits.length > 0 && (
              <ul className="mt-6 max-w-prose space-y-1 text-sm text-muted">
                {credits.map((credit) => (
                  <li key={`${credit.author}-${credit.license}`}>
                    Photograph: {credit.author}. {credit.license}. {credit.source}.
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <ButtonLink href={`/explore/${site.slug}/checkpoints`} className="w-full sm:w-auto">
                Start Exploring
              </ButtonLink>
              <ButtonLink href={`/explore/${site.slug}/lens`} variant="secondary" className="w-full sm:w-auto">
                Open Scanner
              </ButtonLink>
              <SaveDestinationButton slug={site.slug} name={site.name} className="w-full sm:w-auto" />
            </div>
          </div>
          <div className="md:col-span-5">
            <DiscoveryProgress site={site} />
          </div>
        </div>

        <section className="mt-20 border-t border-line py-12">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <h2 className="font-display text-4xl text-primary">Places to find</h2>
              <p className="mt-3 max-w-xl text-muted">
                {site.checkpoints.length} checkpoints are marked here. {withPhotographs} {withPhotographs === 1 ? "has" : "have"} a reference photograph the scanner can compare.
              </p>
            </div>
            <ButtonLink href={`/explore/${site.slug}/checkpoints`} variant="quiet">
              Open the full list
            </ButtonLink>
          </div>
          <div className="mt-8">
            <CheckpointExplorer site={site} variant="index" />
          </div>
        </section>
      </div>
    </article>
  );
}
