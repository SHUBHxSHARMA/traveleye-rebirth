import type { Metadata } from "next";
import { LensView } from "@/components/LensView";
import { MissingSite } from "@/components/MissingSite";
import { getSiteBySlug } from "@/lib/data/sites";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const site = getSiteBySlug(slug);
  return { title: site ? `${site.name} scanner` : "Scanner" };
}

export default async function LensPage({ params }: PageProps) {
  const { slug } = await params;
  const site = getSiteBySlug(slug);
  if (!site) return <MissingSite tone="dark" />;
  return <LensView site={site} />;
}
