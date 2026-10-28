import sharp from "sharp";
import { readFile } from "fs/promises";
import path from "path";
/** Keep in step with MAX_UPLOAD_BYTES in scan-limits.ts. The client must not import this file. */
export const UPLOAD_BYTE_LIMIT = 8 * 1024 * 1024;

const ALLOWED_FORMATS = new Set(["jpeg", "png", "webp"]);

function createSharpInstance(imageBuffer: Buffer) {
  return sharp(imageBuffer, { failOn: "none", limitInputPixels: 48_000_000 });
}

export class ImageValidationError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ImageValidationError";
    this.status = status;
  }
}

/**
 * Reads a visitor photograph and rejects empty, oversized, or unreadable files
 * before any comparison. sharp reports jpeg for JPG files.
 */
export async function readUploadImage(image: Blob): Promise<Buffer> {
  if (image.size === 0) {
    throw new ImageValidationError(400, "The uploaded file is empty.");
  }
  if (image.size > UPLOAD_BYTE_LIMIT) {
    throw new ImageValidationError(413, "That photograph is too large. Use an image under 8 MB.");
  }

  const declaredType = image.type.toLowerCase();
  if (declaredType && !declaredType.startsWith("image/")) {
    throw new ImageValidationError(415, "That file is not a photograph. Use a JPG, PNG, or WebP image.");
  }

  const buffer = Buffer.from(await image.arrayBuffer());
  if (buffer.length === 0) {
    throw new ImageValidationError(400, "The uploaded file is empty.");
  }

  let format: string | undefined;
  try {
    const metadata = await sharp(buffer, { failOn: "error", limitInputPixels: 48_000_000 }).metadata();
    format = metadata.format;
    if (!metadata.width || !metadata.height) {
      throw new ImageValidationError(400, "That image has no visible content.");
    }
  } catch (error) {
    if (error instanceof ImageValidationError) throw error;
    throw new ImageValidationError(400, "That file could not be read as an image.");
  }

  if (!format || !ALLOWED_FORMATS.has(format)) {
    throw new ImageValidationError(415, "Use a JPG, PNG, or WebP photograph.");
  }

  return buffer;
}

export async function averageHash(imageBuffer: Buffer): Promise<string> {
  const { data } = await createSharpInstance(imageBuffer)
    .greyscale()
    .resize(32, 32, { fit: "cover" })
    .raw()
    .toBuffer({ resolveWithObject: true });

  const pixels = [...data];
  const avg = pixels.reduce((sum, value) => sum + value, 0) / pixels.length;
  return pixels.map((value) => (value >= avg ? "1" : "0")).join("");
}

export async function differenceHash(imageBuffer: Buffer): Promise<string> {
  const { data, info } = await createSharpInstance(imageBuffer)
    .greyscale()
    .resize(33, 32, { fit: "cover" })
    .raw()
    .toBuffer({ resolveWithObject: true });

  const width = info.width;
  let hash = "";
  for (let y = 0; y < 32; y += 1) {
    for (let x = 0; x < 31; x += 1) {
      const left = data[y * width + x];
      const right = data[y * width + x + 1];
      hash += left > right ? "1" : "0";
    }
  }
  return hash;
}

export async function combinedHash(imageBuffer: Buffer): Promise<{
  average: string;
  difference: string;
}> {
  const [average, difference] = await Promise.all([
    averageHash(imageBuffer),
    differenceHash(imageBuffer),
  ]);
  return { average, difference };
}

export function hammingDistance(hashA: string, hashB: string): number {
  if (hashA.length === 0 || hashA.length !== hashB.length) {
    return Math.max(hashA.length, hashB.length);
  }
  let distance = 0;
  for (let i = 0; i < hashA.length; i += 1) {
    if (hashA[i] !== hashB[i]) distance += 1;
  }
  return distance;
}

export function combinedDistance(
  capture: { average: string; difference: string },
  reference: { average: string; difference: string },
): number {
  return (
    hammingDistance(capture.average, reference.average) +
    hammingDistance(capture.difference, reference.difference)
  );
}

const referenceHashCache = new Map<string, Promise<{ average: string; difference: string }>>();

export function hashReferenceImage(source: string, buffer: Buffer) {
  const cached = referenceHashCache.get(source);
  if (cached) return cached;
  const pending = combinedHash(buffer).catch((error: unknown) => {
    referenceHashCache.delete(source);
    throw error;
  });
  referenceHashCache.set(source, pending);
  return pending;
}

export async function loadReferenceImage(source: string): Promise<Buffer> {
  if (source.startsWith("/")) {
    const filePath = path.join(process.cwd(), "public", source.replace(/^\//, ""));
    return readFile(filePath);
  }

  const response = await fetch(source);
  if (!response.ok) {
    throw new Error(`Failed to fetch reference image: ${source} (${response.status})`);
  }
  return Buffer.from(await response.arrayBuffer());
}

/**
 * Combined hash length: 32×32 average hash (1024) plus 32×31 difference hash (992).
 * Distance is the number of disagreeing bits. Lower is closer. A random pair is
 * expected near half of these bits, about 1008.
 *
 * Threshold from scripts/evaluate-match.ts on the photographs in public/references
 * (October 2026 run):
 * - Resized copies of the same file (640px, JPEG quality 70) scored 23–469.
 * - The closest pair of different checkpoints scored 572.
 * - 520 is the midpoint of that gap. It accepts every resized copy in that run
 *   and rejects every different-checkpoint pair in that run.
 * - An 80% centre crop scored 478–961, so many crops fall past this line.
 * - A second photograph of the same checkpoint scored 19–1160 (median 812).
 *   This comparison recognises a near-copy of a stored photograph. It does not
 *   recognise a new viewpoint. The threshold is provisional for that reason.
 */
export const HASH_BITS = 1024 + 992;
export const MATCH_THRESHOLD = 520;

/**
 * The winner must be this many bits closer than the next checkpoint at the same
 * destination. Every resized reference in the evaluation was at least 348 bits
 * closer to itself than to any other checkpoint, so 80 does not reject those copies.
 */
export const MATCH_MARGIN = 80;

export function isMatch(distance: number): boolean {
  return distance <= MATCH_THRESHOLD;
}

/** Share of compared bits that agree. This is not a probability. */
export function bitAgreement(distance: number): number {
  if (!Number.isFinite(distance)) return 0;
  return Math.max(0, Math.min(1, (HASH_BITS - distance) / HASH_BITS));
}

export function decideMatch(bestDistance: number, secondDistance?: number) {
  const margin =
    secondDistance === undefined || !Number.isFinite(secondDistance)
      ? Number.POSITIVE_INFINITY
      : secondDistance - bestDistance;
  return {
    matched: Number.isFinite(bestDistance) && bestDistance <= MATCH_THRESHOLD && margin >= MATCH_MARGIN,
    margin,
    bitAgreement: bitAgreement(bestDistance),
  };
}
