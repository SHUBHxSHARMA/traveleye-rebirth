import { readFile } from "fs/promises";
import path from "path";
import sharp from "sharp";
import { combinedDistance, combinedHash } from "../src/lib/image-hash.ts";

const root = path.join(process.cwd(), "public", "references");

const groups: Record<string, string[]> = {
  "red-fort:lahori-gate": ["lahori-gate.jpg", "lahori-gate-user.jpg"],
  "red-fort:chhatta-chowk": ["chhatta-chowk.jpg"],
  "red-fort:naubat-khana": ["naubat-khana.jpg"],
  "red-fort:diwan-i-am": ["diwan-i-am.jpg"],
  "red-fort:diwan-i-khas": ["diwan-i-khas-1.jpg", "diwan-i-khas-2.jpg", "diwan-i-khas-3.jpg"],
  "red-fort:mumtaz-mahal": ["mumtaz-mahal.jpg"],
  "red-fort:rang-mahal": ["rang-mahal.jpg", "rang-mahal-2.jpg", "rang-mahal-user.jpg"],
  "red-fort:moti-masjid": ["moti-masjid-1.jpg", "moti-masjid-2.jpg"],
  "red-fort:hammam": ["hammam.jpg"],
  "red-fort:shahi-burj": ["shahi-burj.jpg"],
  "taj-mahal:mausoleum": ["taj-mahal.jpg"],
  "qutub-minar:minar": ["qutb-minar.jpg"],
  "qutub-minar:iron-pillar": ["iron-pillar-delhi.jpg"],
  "qutub-minar:alai-darwaza": ["alai-darwaza.jpg"],
  "sanchi-stupa:great-stupa": ["sanchi-stupa-1.jpg"],
  "khajuraho:kandariya": ["kandariya-mahadeva.jpg"],
};

async function variants(file: string) {
  const original = await readFile(path.join(root, file));
  const resized = await sharp(original).resize({ width: 640 }).jpeg({ quality: 70 }).toBuffer();
  const meta = await sharp(original).metadata();
  const width = meta.width ?? 1000;
  const height = meta.height ?? 1000;
  const crop = await sharp(original)
    .extract({
      left: Math.round(width * 0.1),
      top: Math.round(height * 0.1),
      width: Math.round(width * 0.8),
      height: Math.round(height * 0.8),
    })
    .jpeg({ quality: 80 })
    .toBuffer();
  return { original, resized, crop };
}

function summarize(label: string, values: number[]) {
  if (values.length === 0) {
    console.log(`${label}: none`);
    return;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const avg = sorted.reduce((sum, value) => sum + value, 0) / sorted.length;
  console.log(
    `${label}: n=${sorted.length} min=${sorted[0]} median=${sorted[Math.floor(sorted.length / 2)]} max=${sorted[sorted.length - 1]} avg=${avg.toFixed(1)}`,
  );
}

const hashes = new Map<string, Awaited<ReturnType<typeof combinedHash>>>();

for (const files of Object.values(groups)) {
  for (const file of files) {
    const { original, resized, crop } = await variants(file);
    hashes.set(`${file}:original`, await combinedHash(original));
    hashes.set(`${file}:resized`, await combinedHash(resized));
    hashes.set(`${file}:crop`, await combinedHash(crop));
  }
}

const sameFile: number[] = [];
const resizedDistances: number[] = [];
const cropDistances: number[] = [];
const sameCheckpoint: number[] = [];
const differentCheckpoint: number[] = [];
const differentSite: number[] = [];

for (const [group, files] of Object.entries(groups)) {
  const site = group.split(":")[0];
  for (const file of files) {
    const original = hashes.get(`${file}:original`)!;
    sameFile.push(combinedDistance(original, original));
    resizedDistances.push(combinedDistance(original, hashes.get(`${file}:resized`)!));
    cropDistances.push(combinedDistance(original, hashes.get(`${file}:crop`)!));
  }
  for (let i = 0; i < files.length; i += 1) {
    for (let j = i + 1; j < files.length; j += 1) {
      const distance = combinedDistance(
        hashes.get(`${files[i]}:original`)!,
        hashes.get(`${files[j]}:original`)!,
      );
      sameCheckpoint.push(distance);
      console.log(`same checkpoint ${files[i]} vs ${files[j]}: ${distance}`);
    }
  }
  for (const [otherGroup, otherFiles] of Object.entries(groups)) {
    if (otherGroup <= group) continue;
    const otherSite = otherGroup.split(":")[0];
    for (const file of files) {
      for (const other of otherFiles) {
        const distance = combinedDistance(
          hashes.get(`${file}:original`)!,
          hashes.get(`${other}:original`)!,
        );
        if (site === otherSite) differentCheckpoint.push(distance);
        else differentSite.push(distance);
      }
    }
  }
}

summarize("identical file", sameFile);
summarize("resized to 640px jpeg q70", resizedDistances);
summarize("centre 80% crop", cropDistances);
summarize("different photo, same checkpoint", sameCheckpoint);
summarize("different checkpoint, same destination", differentCheckpoint);
summarize("different destination", differentSite);

let closestPair = "";
let closestPairDistance = Number.POSITIVE_INFINITY;
for (const [group, files] of Object.entries(groups)) {
  for (const [otherGroup, otherFiles] of Object.entries(groups)) {
    if (otherGroup <= group) continue;
    for (const file of files) {
      for (const other of otherFiles) {
        const distance = combinedDistance(
          hashes.get(`${file}:original`)!,
          hashes.get(`${other}:original`)!,
        );
        if (distance < closestPairDistance) {
          closestPairDistance = distance;
          closestPair = `${file} vs ${other}`;
        }
      }
    }
  }
}
console.log("closest different-checkpoint pair", closestPair, closestPairDistance);
console.log("same-checkpoint pairs", sameCheckpoint.join(", "));

let weakestMargin = Number.POSITIVE_INFINITY;
for (const [group, files] of Object.entries(groups)) {
  for (const file of files) {
    const probe = hashes.get(`${file}:resized`)!;
    let own = Number.POSITIVE_INFINITY;
    let other = Number.POSITIVE_INFINITY;
    for (const [candidateGroup, candidateFiles] of Object.entries(groups)) {
      for (const candidate of candidateFiles) {
        const distance = combinedDistance(probe, hashes.get(`${candidate}:original`)!);
        if (candidateGroup === group) own = Math.min(own, distance);
        else other = Math.min(other, distance);
      }
    }
    const margin = other - own;
    weakestMargin = Math.min(weakestMargin, margin);
    if (margin < 120 || own > 400) {
      console.log(`resize ${file}: own=${own} nearestOther=${other} margin=${margin}`);
    }
  }
}
console.log("weakest resize margin", weakestMargin);
