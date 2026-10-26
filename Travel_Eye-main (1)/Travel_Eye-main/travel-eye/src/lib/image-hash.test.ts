import assert from "node:assert/strict";
import test from "node:test";
import sharp from "sharp";
import { decideMatch, ImageValidationError, MATCH_THRESHOLD, readUploadImage, UPLOAD_BYTE_LIMIT } from "./image-hash.ts";
import { MAX_UPLOAD_BYTES } from "./scan-limits.ts";

test("a near copy of a stored photograph is accepted", () => {
  const decision = decideMatch(0);
  assert.equal(decision.matched, true);
  assert.equal(decision.bitAgreement, 1);
});

test("the worst resized reference in the evaluation set still matches", () => {
  assert.equal(decideMatch(469, 469 + 348).matched, true);
});

test("the closest different-checkpoint pair in the evaluation set does not match", () => {
  assert.ok(572 > MATCH_THRESHOLD);
  assert.equal(decideMatch(572, 700).matched, false);
});

test("a close second checkpoint is not reported as a match", () => {
  assert.equal(decideMatch(400, 470).matched, false);
  assert.equal(decideMatch(400, 480).matched, true);
});

test("readUploadImage accepts a small JPEG", async () => {
  const jpeg = await sharp({
    create: { width: 8, height: 8, channels: 3, background: { r: 20, g: 40, b: 60 } },
  })
    .jpeg()
    .toBuffer();
  const accepted = await readUploadImage(new Blob([jpeg], { type: "image/jpeg" }));
  assert.ok(accepted.length > 0);
});

test("readUploadImage rejects an empty file", async () => {
  await assert.rejects(
    () => readUploadImage(new Blob([], { type: "image/jpeg" })),
    (error: unknown) => error instanceof ImageValidationError && error.status === 400,
  );
});

test("readUploadImage rejects a text file", async () => {
  await assert.rejects(
    () => readUploadImage(new Blob(["not a photograph"], { type: "text/plain" })),
    (error: unknown) => error instanceof ImageValidationError && error.status === 415,
  );
});

test("readUploadImage rejects a file that is not an image even with an image type", async () => {
  await assert.rejects(
    () => readUploadImage(new Blob(["not a photograph"], { type: "image/jpeg" })),
    (error: unknown) => error instanceof ImageValidationError && error.status === 400,
  );
});

test("the scanner and the server use the same size limit", () => {
  assert.equal(MAX_UPLOAD_BYTES, UPLOAD_BYTE_LIMIT);
});

test("readUploadImage rejects an oversized file", async () => {
  const oversized = new Uint8Array(MAX_UPLOAD_BYTES + 1);
  await assert.rejects(
    () => readUploadImage(new Blob([oversized], { type: "image/jpeg" })),
    (error: unknown) => error instanceof ImageValidationError && error.status === 413,
  );
});
