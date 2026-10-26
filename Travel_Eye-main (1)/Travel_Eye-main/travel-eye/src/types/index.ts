export type CheckpointCategory =
  | "gate"
  | "architecture"
  | "sculpture"
  | "engraving"
  | "hall"
  | "mosque"
  | "palace"
  | "tomb"
  | "garden"
  | "tower"
  | "pillar"
  | "stupa"
  | "temple";

export interface ImageCredit {
  author: string;
  license: string;
  source: string;
}

export type DiscoveryMethod = "gps" | "photo_match" | "manual";

export interface Checkpoint {
  id: string;
  slug: string;
  name: string;
  category: CheckpointCategory;
  shortDescription: string;
  story: string;
  /** Omitted when a surveyed point for this structure was not verified. */
  latitude?: number;
  longitude?: number;
  radiusMeters?: number;
  /** Omitted when no photograph of this structure is on record. */
  referenceImageUrl?: string;
  /** Extra reference photos improve scan accuracy */
  referenceImageUrls?: string[];
  imageCredit?: ImageCredit;
  sortOrder: number;
}

export interface Site {
  id: string;
  slug: string;
  name: string;
  city: string;
  country: string;
  description: string;
  overview: string;
  latitude: number;
  longitude: number;
  coverImage: string;
  coverAlt?: string;
  coverCredit?: ImageCredit;
  checkpoints: Checkpoint[];
}

export interface Discovery {
  checkpointId: string;
  method: DiscoveryMethod;
  discoveredAt: string;
}
