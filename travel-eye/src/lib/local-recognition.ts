/**
 * Server-side client for the local OpenCLIP service.
 * LOCAL_RECOGNITION_URL is read only on the server. It is not a NEXT_PUBLIC_ variable.
 */

export const DEFAULT_LOCAL_RECOGNITION_URL = "http://127.0.0.1:8765";
export const LOCAL_RECOGNITION_TIMEOUT_MS = 15_000;
export const NO_MATCH_MESSAGE =
  "No reliable match found. Try a clearer photograph of one place, or choose it from the list.";

export type LocalOutcome =
  | { outcome: "match"; checkpointId: string }
  | { outcome: "no_match" }
  | { outcome: "fallback" };

export type HashFallback<T> =
  | {
      kind: "match";
      checkpoint: T;
      bitAgreement: number;
      bestDistance: number;
      margin: number | null;
    }
  | { kind: "no_match"; bestDistance: number | null; margin: number | null }
  | { kind: "unavailable" }
  | { kind: "invalid_image"; message: string }
  | { kind: "error"; message: string };

export type ResolvedScan<T> =
  | { kind: "local_match"; checkpoint: T }
  | { kind: "local_no_match" }
  | HashFallback<T>;

export function localRecognitionUrl(): string {
  const configured = process.env.LOCAL_RECOGNITION_URL?.trim();
  const base = configured ? configured : DEFAULT_LOCAL_RECOGNITION_URL;
  return base.replace(/\/+$/, "");
}

export function interpretLocalResponse(payload: unknown): LocalOutcome {
  if (!payload || typeof payload !== "object") return { outcome: "fallback" };
  const record = payload as { status?: unknown; code?: unknown; checkpointId?: unknown };
  const status = record.status;
  const code = record.code;
  if (code !== undefined && code !== status) return { outcome: "fallback" };
  if (status === "no_match") return { outcome: "no_match" };
  if (status === "match" && typeof record.checkpointId === "string" && record.checkpointId.length > 0) {
    return { outcome: "match", checkpointId: record.checkpointId };
  }
  return { outcome: "fallback" };
}

export async function askLocalRecognition(
  image: Blob,
  siteSlug: string,
  options?: {
    fetchImpl?: typeof fetch;
    timeoutMs?: number;
    serviceUrl?: string;
  },
): Promise<LocalOutcome> {
  const form = new FormData();
  form.append("image", image, "scan.jpg");
  form.append("siteSlug", siteSlug);
  const fetchImpl = options?.fetchImpl ?? fetch;
  const timeoutMs = options?.timeoutMs ?? LOCAL_RECOGNITION_TIMEOUT_MS;
  const base = (options?.serviceUrl ?? localRecognitionUrl()).replace(/\/+$/, "");
  try {
    const response = await fetchImpl(`${base}/recognize`, {
      method: "POST",
      body: form,
      redirect: "error",
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response.ok) return { outcome: "fallback" };
    try {
      return interpretLocalResponse(await response.json());
    } catch {
      return { outcome: "fallback" };
    }
  } catch {
    return { outcome: "fallback" };
  }
}

/**
 * An explicit local no_match is returned as uncertainty.
 * The hash matcher runs only when the local service did not accept or reject the photograph.
 */
export async function resolveScan<T extends { id: string }>(args: {
  checkpoints: readonly T[];
  local: LocalOutcome;
  hashFallback: () => Promise<HashFallback<T>>;
}): Promise<ResolvedScan<T>> {
  const local = args.local;
  if (local.outcome === "no_match") return { kind: "local_no_match" };
  if (local.outcome === "match") {
    const checkpoint = args.checkpoints.find((item) => item.id === local.checkpointId);
    if (checkpoint) return { kind: "local_match", checkpoint };
  }
  return args.hashFallback();
}
