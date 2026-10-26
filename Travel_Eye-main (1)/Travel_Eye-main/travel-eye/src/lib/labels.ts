import type { CheckpointCategory, DiscoveryMethod } from "@/types";

export const CATEGORY_LABEL: Record<CheckpointCategory, string> = {
  gate: "Gate",
  architecture: "Architecture",
  sculpture: "Sculpture",
  engraving: "Engraving",
  hall: "Hall",
  mosque: "Mosque",
  palace: "Palace",
  tomb: "Tomb",
  garden: "Garden",
  tower: "Tower",
  pillar: "Pillar",
  stupa: "Stupa",
  temple: "Temple",
};

export const METHOD_LABEL: Record<DiscoveryMethod, string> = {
  gps: "Found nearby",
  photo_match: "Matched from a photograph",
  manual: "Marked while exploring",
};
