import assert from "node:assert/strict";
import test from "node:test";
import sharp from "sharp";
import {
  askLocalRecognition,
  DEFAULT_LOCAL_RECOGNITION_URL,
  interpretLocalResponse,
  localRecognitionUrl,
  NO_MATCH_MESSAGE,
  resolveScan,
} from "./local-recognition.ts";

const lahori = { id: "lahori-gate", name: "Lahori Gate" };
const toranas = { id: "sanchi-toranas", name: "Gateways" };

async function jpegBlob() {
  const jpeg = await sharp({
    create: { width: 8, height: 8, channels: 3, background: { r: 20, g: 40, b: 60 } },
  })
    .jpeg()
    .toBuffer();
  return new Blob([new Uint8Array(jpeg)], { type: "image/jpeg" });
}

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("the service URL defaults to the local loopback address", () => {
  const previous = process.env.LOCAL_RECOGNITION_URL;
  const publicOverride = process.env.NEXT_PUBLIC_LOCAL_RECOGNITION_URL;
  delete process.env.LOCAL_RECOGNITION_URL;
  process.env.NEXT_PUBLIC_LOCAL_RECOGNITION_URL = "http://203.0.113.8:8765";
  try {
    assert.equal(localRecognitionUrl(), DEFAULT_LOCAL_RECOGNITION_URL);
    assert.equal(DEFAULT_LOCAL_RECOGNITION_URL, "http://127.0.0.1:8765");
  } finally {
    if (previous === undefined) delete process.env.LOCAL_RECOGNITION_URL;
    else process.env.LOCAL_RECOGNITION_URL = previous;
    if (publicOverride === undefined) delete process.env.NEXT_PUBLIC_LOCAL_RECOGNITION_URL;
    else process.env.NEXT_PUBLIC_LOCAL_RECOGNITION_URL = publicOverride;
  }
});

test("a server environment variable can point at another loopback port", () => {
  const previous = process.env.LOCAL_RECOGNITION_URL;
  process.env.LOCAL_RECOGNITION_URL = "http://127.0.0.1:9000/";
  try {
    assert.equal(localRecognitionUrl(), "http://127.0.0.1:9000");
  } finally {
    if (previous === undefined) delete process.env.LOCAL_RECOGNITION_URL;
    else process.env.LOCAL_RECOGNITION_URL = previous;
  }
});

test("an accepted local response keeps the checkpoint id", () => {
  assert.deepEqual(
    interpretLocalResponse({
      status: "match",
      code: "match",
      checkpointId: "lahori-gate",
      checkpointName: "Lahori Gate",
      bestSimilarity: 1,
      margin: 0.2,
      referenceCount: 2,
    }),
    { outcome: "match", checkpointId: "lahori-gate" },
  );
});

test("an explicit no_match drops any checkpoint name", () => {
  assert.deepEqual(
    interpretLocalResponse({
      status: "no_match",
      code: "no_match",
      checkpointId: "lahori-gate",
      checkpointName: "Lahori Gate",
      bestSimilarity: 0.81,
      margin: 0.01,
    }),
    { outcome: "no_match" },
  );
});

test("a contradictory or incomplete local response is not a recognition", () => {
  assert.equal(interpretLocalResponse({ status: "match", code: "no_match", checkpointId: "lahori-gate" }).outcome, "fallback");
  assert.equal(interpretLocalResponse({ status: "match", code: "match" }).outcome, "fallback");
  assert.equal(interpretLocalResponse({ status: "match", code: "match", checkpointId: "" }).outcome, "fallback");
  assert.equal(interpretLocalResponse("ok").outcome, "fallback");
});

test("askLocalRecognition posts the image and siteSlug fields", async () => {
  const image = await jpegBlob();
  let seenUrl = "";
  let seenSlug = "";
  let seenImage = false;
  const fetchImpl: typeof fetch = async (url, init) => {
    seenUrl = String(url);
    const form = init?.body as FormData;
    seenSlug = String(form.get("siteSlug"));
    seenImage = form.get("image") instanceof Blob;
    return jsonResponse(200, { status: "match", code: "match", checkpointId: "lahori-gate" });
  };
  const outcome = await askLocalRecognition(image, "red-fort", {
    fetchImpl,
    serviceUrl: "http://127.0.0.1:8765",
  });
  assert.equal(seenUrl, "http://127.0.0.1:8765/recognize");
  assert.equal(seenSlug, "red-fort");
  assert.equal(seenImage, true);
  assert.deepEqual(outcome, { outcome: "match", checkpointId: "lahori-gate" });
});

test("an explicit no_match does not call the hash matcher", async () => {
  let hashed = false;
  const resolved = await resolveScan({
    checkpoints: [lahori],
    local: { outcome: "no_match" },
    hashFallback: async () => {
      hashed = true;
      return { kind: "match", checkpoint: lahori, bitAgreement: 1, bestDistance: 0, margin: null };
    },
  });
  assert.equal(hashed, false);
  assert.deepEqual(resolved, { kind: "local_no_match" });
  assert.equal(JSON.stringify(resolved).includes("Lahori"), false);
  assert.equal(NO_MATCH_MESSAGE.includes("Lahori"), false);
});

test("an accepted checkpoint is returned without hashing", async () => {
  let hashed = false;
  const resolved = await resolveScan({
    checkpoints: [lahori, toranas],
    local: { outcome: "match", checkpointId: "sanchi-toranas" },
    hashFallback: async () => {
      hashed = true;
      return { kind: "no_match", bestDistance: null, margin: null };
    },
  });
  assert.equal(hashed, false);
  assert.equal(resolved.kind, "local_match");
  if (resolved.kind === "local_match") assert.equal(resolved.checkpoint.id, "sanchi-toranas");
});

test("a checkpoint id outside this destination falls back to hashing", async () => {
  let hashed = false;
  const resolved = await resolveScan({
    checkpoints: [lahori],
    local: { outcome: "match", checkpointId: "taj-mahal-mausoleum" },
    hashFallback: async () => {
      hashed = true;
      return { kind: "no_match", bestDistance: 600, margin: 20 };
    },
  });
  assert.equal(hashed, true);
  assert.equal(resolved.kind, "no_match");
});

test("an unavailable local service uses the hash result", async () => {
  const resolved = await resolveScan({
    checkpoints: [lahori],
    local: { outcome: "fallback" },
    hashFallback: async () => ({
      kind: "match",
      checkpoint: lahori,
      bitAgreement: 0.9,
      bestDistance: 40,
      margin: 200,
    }),
  });
  assert.equal(resolved.kind, "match");
  if (resolved.kind === "match") assert.equal(resolved.checkpoint.id, "lahori-gate");
});

test("an HTTP error from the local service is a fallback, not a match", async () => {
  const image = await jpegBlob();
  const outcome = await askLocalRecognition(image, "red-fort", {
    serviceUrl: "http://127.0.0.1:8765",
    fetchImpl: async () => jsonResponse(500, { status: "match", code: "match", checkpointId: "lahori-gate" }),
  });
  assert.equal(outcome.outcome, "fallback");
});

test("a malformed local body is a fallback, not a match", async () => {
  const image = await jpegBlob();
  const outcome = await askLocalRecognition(image, "red-fort", {
    serviceUrl: "http://127.0.0.1:8765",
    fetchImpl: async () => new Response("<html>nope</html>", { status: 200 }),
  });
  assert.equal(outcome.outcome, "fallback");
});

test("a timeout or connection failure falls back", async () => {
  const image = await jpegBlob();
  const hanging: typeof fetch = (_url, init) =>
    new Promise((_resolve, reject) => {
      const signal = init?.signal;
      if (!signal) {
        reject(new Error("missing timeout"));
        return;
      }
      signal.addEventListener("abort", () => reject(signal.reason));
    });
  const outcome = await askLocalRecognition(image, "red-fort", {
    fetchImpl: hanging,
    timeoutMs: 20,
    serviceUrl: "http://127.0.0.1:8765",
  });
  assert.equal(outcome.outcome, "fallback");
});
