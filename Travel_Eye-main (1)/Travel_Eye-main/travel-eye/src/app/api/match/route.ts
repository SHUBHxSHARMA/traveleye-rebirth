import { NextResponse } from "next/server";
import { referenceSources } from "@/lib/checkpoints";
import { getSiteBySlug } from "@/lib/data/sites";
import {
  combinedDistance,
  combinedHash,
  decideMatch,
  hashReferenceImage,
  ImageValidationError,
  loadReferenceImage,
  readUploadImage,
} from "@/lib/image-hash";
import {
  askLocalRecognition,
  NO_MATCH_MESSAGE,
  resolveScan,
  type HashFallback,
} from "@/lib/local-recognition";
import type { Checkpoint, Site } from "@/types";

function jsonError(status: number, message: string, code: string) {
  return NextResponse.json({ message, code }, { status });
}

async function hashScan(site: Site, captureBuffer: Buffer): Promise<HashFallback<Checkpoint>> {
  let captureHashes: Awaited<ReturnType<typeof combinedHash>>;
  try {
    captureHashes = await combinedHash(captureBuffer);
  } catch {
    return { kind: "invalid_image", message: "That photograph could not be processed." };
  }

  const comparable = site.checkpoints.filter((checkpoint) => referenceSources(checkpoint).length > 0);
  if (comparable.length === 0) return { kind: "unavailable" };

  const perCheckpoint: { checkpoint: Checkpoint; distance: number }[] = [];
  let loadedReferences = 0;

  for (const checkpoint of comparable) {
    let bestForCheckpoint = Number.POSITIVE_INFINITY;

    for (const source of referenceSources(checkpoint)) {
      try {
        const referenceBuffer = await loadReferenceImage(source);
        const referenceHashes = await hashReferenceImage(source, referenceBuffer);
        const distance = combinedDistance(captureHashes, referenceHashes);
        loadedReferences += 1;
        bestForCheckpoint = Math.min(bestForCheckpoint, distance);
      } catch {
        // A broken reference is skipped. It is never treated as a match.
      }
    }

    if (bestForCheckpoint < Number.POSITIVE_INFINITY) {
      perCheckpoint.push({ checkpoint, distance: bestForCheckpoint });
    }
  }

  if (loadedReferences === 0) {
    return { kind: "error", message: "Reference photographs could not be loaded. Please try again later." };
  }

  perCheckpoint.sort((a, b) => a.distance - b.distance);
  const best = perCheckpoint[0];
  const second = perCheckpoint[1];
  const decision = best ? decideMatch(best.distance, second?.distance) : null;
  const winner =
    best &&
    decision?.matched &&
    site.checkpoints.some((checkpoint) => checkpoint.id === best.checkpoint.id) &&
    referenceSources(best.checkpoint).length > 0
      ? best
      : null;

  if (!winner || !decision) {
    return {
      kind: "no_match",
      bestDistance: best?.distance ?? null,
      margin: decision && Number.isFinite(decision.margin) ? decision.margin : null,
    };
  }

  return {
    kind: "match",
    checkpoint: winner.checkpoint,
    bitAgreement: decision.bitAgreement,
    bestDistance: winner.distance,
    margin: Number.isFinite(decision.margin) ? decision.margin : null,
  };
}

function hashResponse(result: HashFallback<Checkpoint>) {
  if (result.kind === "match") {
    // bitAgreement is the fraction of 2016 hash bits that agree. It is not a probability.
    return NextResponse.json({
      match: result.checkpoint,
      bitAgreement: result.bitAgreement,
      bestDistance: result.bestDistance,
      margin: result.margin,
    });
  }
  if (result.kind === "no_match") {
    return NextResponse.json({
      message: NO_MATCH_MESSAGE,
      code: "no_match",
      bestDistance: result.bestDistance,
      margin: result.margin,
    });
  }
  if (result.kind === "unavailable") {
    return NextResponse.json({
      message:
        "Reference photographs are not on record for this destination yet. Open the place list and read the history there.",
      code: "unavailable",
    });
  }
  if (result.kind === "invalid_image") return jsonError(400, result.message, "invalid_image");
  return jsonError(500, result.message, "error");
}

export async function POST(request: Request) {
  try {
    let formData: FormData;
    try {
      formData = await request.formData();
    } catch {
      return jsonError(400, "The scan request could not be read.", "invalid_image");
    }

    const image = formData.get("image");
    const siteSlug = formData.get("siteSlug");

    if (!(image instanceof Blob) || typeof siteSlug !== "string" || siteSlug.length === 0) {
      return jsonError(400, "Choose a photograph and a destination, then scan again.", "invalid_image");
    }

    const site = getSiteBySlug(siteSlug);
    if (!site) {
      return jsonError(404, "This destination is not in the guide.", "not_found");
    }

    let captureBuffer: Buffer;
    try {
      captureBuffer = await readUploadImage(image);
    } catch (error) {
      if (error instanceof ImageValidationError) {
        return jsonError(error.status, error.message, "invalid_image");
      }
      return jsonError(400, "That file could not be read as an image.", "invalid_image");
    }

    const forward = new Blob([new Uint8Array(captureBuffer)], {
      type: image.type.startsWith("image/") ? image.type : "image/jpeg",
    });
    const local = await askLocalRecognition(forward, siteSlug);
    const resolved = await resolveScan({
      checkpoints: site.checkpoints,
      local,
      hashFallback: () => hashScan(site, captureBuffer),
    });

    if (resolved.kind === "local_match") {
      return NextResponse.json({ match: resolved.checkpoint });
    }
    if (resolved.kind === "local_no_match") {
      return NextResponse.json({ message: NO_MATCH_MESSAGE, code: "no_match" });
    }
    return hashResponse(resolved);
  } catch {
    return jsonError(500, "The photograph could not be compared. Try again.", "error");
  }
}
