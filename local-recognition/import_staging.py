"""Validate photographs staged for the local reference gallery.

The script reads images and writes a report. It does not download files, and it
does not change the live gallery, the manifest, the model, or the thresholds.

Stage one photograph on Windows PowerShell:

    $stage = "E:\\TravelEye-Rebirth\\local-recognition\\import-staging\\red-fort\\moti-masjid"
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    Copy-Item "C:\\path\\to\\your-photo.jpg" -Destination $stage
    @'
    {
      "source_page": "https://commons.wikimedia.org/wiki/File:Your_File.jpg",
      "author": "Name as given on the source page",
      "licence": "CC BY-SA 4.0",
      "licence_url": "https://creativecommons.org/licenses/by-sa/4.0"
    }
    '@ | Set-Content -Encoding utf8 "$stage\\your-photo.jpg.json"

    & "E:\\TravelEye-Rebirth\\local-recognition\\.venv\\Scripts\\python.exe" `
      "E:\\TravelEye-Rebirth\\local-recognition\\import_staging.py"

Use the author and licence printed on the source page. Do not copy placeholder
text. A near-duplicate warning does not reject the photograph.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from recognition import DESTINATIONS, MAX_PIXELS

SCRIPT_DIR = Path(__file__).resolve().parent
STAGING_DIR = SCRIPT_DIR / "import-staging"
MANIFEST_PATH = SCRIPT_DIR / "reference_manifest.csv"
REPORT_CSV = STAGING_DIR / "validation_report.csv"
REPORT_TXT = STAGING_DIR / "validation_report.txt"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_FILE_BYTES = 20 * 1024 * 1024
MIN_EDGE = 64
MAX_EDGE = 16_000
# Warn only. A low distance does not reject a distinct viewpoint.
NEAR_DUPLICATE_DISTANCE = 4
HASH_SIZE = 8

REQUIRED_METADATA = ("source_page", "author", "licence", "licence_url")


@dataclass
class Limits:
    max_bytes: int = MAX_FILE_BYTES
    max_pixels: int = MAX_PIXELS
    min_edge: int = MIN_EDGE
    max_edge: int = MAX_EDGE


@dataclass
class KnownFile:
    path: Path
    sha256: str
    average_hash: int | None
    origin: str


@dataclass
class CandidateResult:
    path: Path
    destination_slug: str = ""
    checkpoint_id: str = ""
    status: str = "failed"
    sha256: str = ""
    image_format: str = ""
    width: int = 0
    height: int = 0
    byte_size: int = 0
    source_page: str = ""
    author: str = ""
    licence: str = ""
    licence_url: str = ""
    failures: list[str] = field(default_factory=list)
    review_reasons: list[str] = field(default_factory=list)
    near_duplicate_of: list[str] = field(default_factory=list)
    average_hash: int | None = None

    def finish(self) -> None:
        blocking_review = [
            reason
            for reason in self.review_reasons
            if not reason.startswith("Likely near-duplicate")
        ]
        if self.failures:
            self.status = "failed"
        elif blocking_review:
            self.status = "needs_review"
        else:
            self.status = "passed"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_hash(image: Image.Image, size: int = HASH_SIZE) -> int:
    gray = image.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = gray.tobytes()
    average = sum(pixels) / len(pixels)
    bits = 0
    for index, pixel in enumerate(pixels):
        if pixel >= average:
            bits |= 1 << index
    return bits


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def gallery_files(manifest_path: Path) -> list[KnownFile]:
    if not manifest_path.is_file():
        return []
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    known: list[KnownFile] = []
    for row in rows:
        if row.get("collection") not in {"existing", "added"}:
            continue
        raw_path = row.get("local_path", "").strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        if not path.is_file():
            continue
        known.append(
            KnownFile(
                path=path,
                sha256=file_sha256(path),
                average_hash=hash_image_file(path),
                origin="gallery",
            )
        )
    return known


def hash_image_file(path: Path) -> int | None:
    try:
        with Image.open(path) as image:
            image.load()
            return average_hash(image)
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError):
        return None


def staged_images(staging_dir: Path) -> list[Path]:
    if not staging_dir.is_dir():
        return []
    files = [
        path
        for path in staging_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return sorted(files)


def identifiers_from_path(staging_dir: Path, path: Path) -> tuple[str, str, str | None]:
    try:
        relative = path.relative_to(staging_dir)
    except ValueError:
        return "", "", "The file is outside the staging directory."
    parts = relative.parts
    if len(parts) != 3:
        return "", "", "Place the file in import-staging/<destination-slug>/<checkpoint-id>/filename."
    destination_slug, checkpoint_id, _filename = parts
    if destination_slug not in DESTINATIONS:
        return destination_slug, checkpoint_id, f"Unknown destination slug: {destination_slug}."
    if checkpoint_id not in DESTINATIONS[destination_slug]:
        return destination_slug, checkpoint_id, f"Unknown checkpoint id for {destination_slug}: {checkpoint_id}."
    return destination_slug, checkpoint_id, None


def read_metadata(path: Path) -> tuple[dict[str, str], list[str], list[str]]:
    sidecar = path.with_name(path.name + ".json")
    failures: list[str] = []
    review: list[str] = []
    if not sidecar.is_file():
        review.append("Metadata file is missing. Source page, author, licence, and licence URL are required.")
        return {}, failures, review
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        review.append("Metadata file could not be read as JSON. No attribution was guessed.")
        return {}, failures, review
    if not isinstance(payload, dict):
        review.append("Metadata file must be a JSON object. No attribution was guessed.")
        return {}, failures, review
    values = {key: value.strip() if isinstance(value, str) else "" for key, value in payload.items()}
    for field_name in REQUIRED_METADATA:
        if not values.get(field_name, "").strip():
            review.append(f"Missing {field_name}. No value was invented.")
    for field_name in ("source_page", "licence_url"):
        value = values.get(field_name, "").strip()
        if value and not valid_http_url(value):
            failures.append(f"{field_name} is not an http or https URL.")
    direct = values.get("direct_image_url", "").strip()
    if direct and not valid_http_url(direct):
        failures.append("direct_image_url is not an http or https URL.")
    return values, failures, review


def inspect_image(path: Path, limits: Limits) -> tuple[str, int, int, int | None, list[str]]:
    failures: list[str] = []
    byte_size = path.stat().st_size
    if byte_size == 0:
        failures.append("The file is empty.")
        return "", 0, 0, None, failures
    if byte_size > limits.max_bytes:
        failures.append(f"The file is {byte_size} bytes. The staging limit is {limits.max_bytes} bytes.")
        return "", 0, 0, None, failures
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        failures.append("Use a .jpg, .jpeg, .png, or .webp file.")
        return "", 0, 0, None, failures
    try:
        with Image.open(path) as image:
            image_format = image.format or ""
            width, height = image.size
            if image_format not in ALLOWED_FORMATS:
                failures.append(f"Decoded format {image_format or 'unknown'} is not JPEG, PNG, or WebP.")
                return image_format, width, height, None, failures
            if width < limits.min_edge or height < limits.min_edge:
                failures.append(f"The image is {width} by {height}. Each edge must be at least {limits.min_edge} pixels.")
            if width > limits.max_edge or height > limits.max_edge:
                failures.append(f"The image is {width} by {height}. Each edge must be at most {limits.max_edge} pixels.")
            if width * height > limits.max_pixels:
                failures.append(f"The image has {width * height} pixels. The limit is {limits.max_pixels}.")
            image.load()
            perceptual = average_hash(image)
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError):
        failures.append("The file could not be decoded as an image.")
        return "", 0, 0, None, failures
    return image_format, width, height, perceptual, failures


def validate_staging(
    staging_dir: Path,
    manifest_path: Path,
    limits: Limits | None = None,
) -> list[CandidateResult]:
    limits = limits or Limits()
    known = gallery_files(manifest_path)
    results: list[CandidateResult] = []
    for path in staged_images(staging_dir):
        result = CandidateResult(path=path, byte_size=path.stat().st_size, sha256=file_sha256(path))
        destination_slug, checkpoint_id, identity_error = identifiers_from_path(staging_dir, path)
        result.destination_slug = destination_slug
        result.checkpoint_id = checkpoint_id
        if identity_error:
            result.failures.append(identity_error)
        metadata, metadata_failures, review_reasons = read_metadata(path)
        result.failures.extend(metadata_failures)
        result.review_reasons.extend(review_reasons)
        result.source_page = metadata.get("source_page", "")
        result.author = metadata.get("author", "")
        result.licence = metadata.get("licence", "")
        result.licence_url = metadata.get("licence_url", "")

        image_format, width, height, perceptual, image_failures = inspect_image(path, limits)
        result.image_format = image_format
        result.width = width
        result.height = height
        result.average_hash = perceptual
        result.failures.extend(image_failures)

        exact = [
            item.path
            for item in known
            if item.sha256 == result.sha256 and item.path.resolve() != path.resolve()
        ]
        if exact:
            result.failures.append("SHA-256 matches an existing file: " + "; ".join(str(item) for item in exact))
        if perceptual is not None and not exact:
            for item in known:
                if item.average_hash is None or item.path.resolve() == path.resolve():
                    continue
                distance = hamming(perceptual, item.average_hash)
                if distance <= NEAR_DUPLICATE_DISTANCE:
                    result.near_duplicate_of.append(f"{item.origin}: {item.path} (hash distance {distance})")
            if result.near_duplicate_of:
                result.review_reasons.append(
                    "Likely near-duplicate by average hash. This warning does not reject a distinct viewpoint."
                )
        result.finish()
        results.append(result)
        known.append(
            KnownFile(path=path, sha256=result.sha256, average_hash=result.average_hash, origin="staged")
        )
    return results


def write_reports(results: list[CandidateResult], csv_path: Path, text_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "destination_slug",
        "checkpoint_id",
        "status",
        "sha256",
        "format",
        "width",
        "height",
        "byte_size",
        "source_page",
        "author",
        "licence",
        "licence_url",
        "failures",
        "review_reasons",
        "near_duplicate_of",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "path": str(result.path),
                    "destination_slug": result.destination_slug,
                    "checkpoint_id": result.checkpoint_id,
                    "status": result.status,
                    "sha256": result.sha256,
                    "format": result.image_format,
                    "width": result.width,
                    "height": result.height,
                    "byte_size": result.byte_size,
                    "source_page": result.source_page,
                    "author": result.author,
                    "licence": result.licence,
                    "licence_url": result.licence_url,
                    "failures": " | ".join(result.failures),
                    "review_reasons": " | ".join(result.review_reasons),
                    "near_duplicate_of": " | ".join(result.near_duplicate_of),
                }
            )
    counts = {"passed": 0, "needs_review": 0, "failed": 0}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    lines = [
        "Reference import validation",
        "This report does not add, remove, rename, or overwrite gallery files.",
        f"Candidates: {len(results)}. Passed: {counts['passed']}. Needs review: {counts['needs_review']}. Failed: {counts['failed']}.",
        "A near-duplicate note is a warning. It is not a rejection by itself.",
        "",
    ]
    if not results:
        lines.append("No staged image files were found.")
    for result in results:
        lines.append(f"{result.status.upper()}  {result.path}")
        if result.failures:
            lines.append("  Failures: " + " | ".join(result.failures))
        if result.review_reasons:
            lines.append("  Review: " + " | ".join(result.review_reasons))
        if result.near_duplicate_of:
            lines.append("  Near duplicates: " + " | ".join(result.near_duplicate_of))
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate staged reference photographs without changing the gallery.")
    parser.add_argument("--staging", type=Path, default=STAGING_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--report-csv", type=Path, default=None)
    parser.add_argument("--report-txt", type=Path, default=None)
    args = parser.parse_args(argv)
    staging = args.staging
    csv_path = args.report_csv or (staging / "validation_report.csv")
    text_path = args.report_txt or (staging / "validation_report.txt")
    results = validate_staging(staging, args.manifest)
    write_reports(results, csv_path, text_path)
    print(text_path.read_text(encoding="utf-8"))
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
