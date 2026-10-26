"""Tests for staged reference validation. They use temporary files only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from import_staging import Limits, validate_staging, write_reports


def write_jpeg(
    path: Path,
    color: tuple[int, int, int],
    size: tuple[int, int] = (80, 80),
    quality: int = 95,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="JPEG", quality=quality)


def write_metadata(path: Path, **overrides: str) -> None:
    payload = {
        "source_page": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        "author": "Example Photographer",
        "licence": "CC BY-SA 4.0",
        "licence_url": "https://creativecommons.org/licenses/by-sa/4.0",
    }
    payload.update(overrides)
    path.with_name(path.name + ".json").write_text(json.dumps(payload), encoding="utf-8")


class ImportStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.staging = self.root / "import-staging"
        self.gallery = self.root / "gallery"
        self.manifest = self.root / "manifest.csv"
        self.gallery.mkdir()
        self.manifest.write_text(
            "collection,destination_slug,checkpoint_id,local_path,source_page,direct_image_url,author,licence,licence_url,stored_form,viewpoint,attribution_requirements\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_gallery_file(self, name: str = "stored.jpg") -> Path:
        path = self.gallery / name
        write_jpeg(path, (20, 40, 60))
        with self.manifest.open("a", encoding="utf-8") as handle:
            handle.write(
                f"added,red-fort,moti-masjid,{path},https://example.test/source,,Example,CC BY 4.0,https://creativecommons.org/licenses/by/4.0,original,test,test\n"
            )
        return path

    def test_valid_image_passes(self) -> None:
        photo = self.staging / "red-fort" / "moti-masjid" / "marble-courtyard.jpg"
        write_jpeg(photo, (240, 240, 240))
        write_metadata(photo)
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "passed")
        self.assertEqual(results[0].checkpoint_id, "moti-masjid")
        self.assertEqual(results[0].failures, [])

    def test_invalid_image_fails(self) -> None:
        photo = self.staging / "red-fort" / "moti-masjid" / "broken.jpg"
        photo.parent.mkdir(parents=True)
        photo.write_bytes(b"\xff\xd8\xff\xd8not-a-jpeg")
        write_metadata(photo)
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(results[0].status, "failed")
        self.assertTrue(any("decoded" in reason.lower() for reason in results[0].failures))

    def test_missing_metadata_needs_review(self) -> None:
        photo = self.staging / "taj-mahal" / "taj-mahal-gateway" / "gate.jpg"
        write_jpeg(photo, (180, 160, 120))
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(results[0].status, "needs_review")
        self.assertTrue(any("author" in reason.lower() or "metadata" in reason.lower() for reason in results[0].review_reasons))
        self.assertEqual(results[0].author, "")

    def test_blank_author_needs_review(self) -> None:
        photo = self.staging / "sanchi-stupa" / "sanchi-ashokan-pillar" / "pillar.jpg"
        write_jpeg(photo, (90, 90, 90))
        write_metadata(photo, author="  ")
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(results[0].status, "needs_review")
        self.assertTrue(any("author" in reason.lower() for reason in results[0].review_reasons))

    def test_unknown_checkpoint_fails(self) -> None:
        photo = self.staging / "red-fort" / "not-a-checkpoint" / "photo.jpg"
        write_jpeg(photo, (10, 20, 30))
        write_metadata(photo)
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(results[0].status, "failed")
        self.assertTrue(any("Unknown checkpoint" in reason for reason in results[0].failures))

    def test_exact_duplicate_fails(self) -> None:
        stored = self.add_gallery_file()
        photo = self.staging / "red-fort" / "moti-masjid" / "copy.jpg"
        photo.parent.mkdir(parents=True)
        photo.write_bytes(stored.read_bytes())
        write_metadata(photo)
        before = stored.read_bytes()
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(results[0].status, "failed")
        self.assertTrue(any("SHA-256" in reason for reason in results[0].failures))
        self.assertEqual(stored.read_bytes(), before)

    def test_near_duplicate_warns_without_failing(self) -> None:
        stored = self.add_gallery_file("plain.jpg")
        photo = self.staging / "red-fort" / "moti-masjid" / "plain-again.jpg"
        write_jpeg(photo, (20, 40, 60), quality=40)
        write_metadata(photo)
        self.assertNotEqual(photo.read_bytes(), stored.read_bytes())
        results = validate_staging(self.staging, self.manifest)
        self.assertEqual(results[0].status, "passed")
        self.assertTrue(results[0].near_duplicate_of)
        self.assertTrue(any("does not reject" in reason for reason in results[0].review_reasons))

    def test_oversized_and_tiny_images_fail(self) -> None:
        tiny = self.staging / "qutub-minar" / "qutub-quwwat-ul-islam" / "tiny.jpg"
        write_jpeg(tiny, (1, 2, 3), size=(16, 16))
        write_metadata(tiny)
        large = self.staging / "qutub-minar" / "qutub-quwwat-ul-islam" / "large.jpg"
        write_jpeg(large, (4, 5, 6))
        write_metadata(large)
        results = validate_staging(self.staging, self.manifest, Limits(max_bytes=large.stat().st_size - 1))
        by_name = {result.path.name: result for result in results}
        self.assertEqual(by_name["tiny.jpg"].status, "failed")
        self.assertTrue(any("edge" in reason for reason in by_name["tiny.jpg"].failures))
        self.assertEqual(by_name["large.jpg"].status, "failed")
        self.assertTrue(any("bytes" in reason for reason in by_name["large.jpg"].failures))

    def test_report_mentions_each_outcome(self) -> None:
        valid = self.staging / "khajuraho" / "khajuraho-lakshmana" / "temple.jpg"
        write_jpeg(valid, (200, 180, 140))
        write_metadata(valid)
        review = self.staging / "khajuraho" / "khajuraho-vishvanatha" / "temple.jpg"
        write_jpeg(review, (30, 60, 90))
        results = validate_staging(self.staging, self.manifest)
        csv_path = self.root / "report.csv"
        text_path = self.root / "report.txt"
        write_reports(results, csv_path, text_path)
        text = text_path.read_text(encoding="utf-8")
        self.assertIn("PASSED", text)
        self.assertIn("NEEDS_REVIEW", text)
        self.assertIn("does not add, remove, rename, or overwrite", text)


if __name__ == "__main__":
    unittest.main()
