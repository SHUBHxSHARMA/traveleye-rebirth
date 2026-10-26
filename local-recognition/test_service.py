"""HTTP tests for the local recognition service.

Model inference is replaced with fixed vectors. The real OpenCLIP weights
are exercised separately by posting a stored photograph to the running service.
"""

from __future__ import annotations

import unittest
from io import BytesIO

import torch
import torch.nn.functional as F
from fastapi.testclient import TestClient
from PIL import Image

from recognition import RecognitionEngine, ReferenceEmbedding
from service import create_app


def unit(*values: float) -> torch.Tensor:
    return F.normalize(torch.tensor(values, dtype=torch.float32), dim=0)


def tiny_jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (180, 40, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


class FixedEngine(RecognitionEngine):
    def __init__(self, query: torch.Tensor, references: list[ReferenceEmbedding]) -> None:
        super().__init__(
            device=torch.device("cpu"),
            model=torch.nn.Identity(),
            preprocess=None,
            references=references,
            min_similarity=0.97,
            min_margin=0.05,
        )
        self.query = query

    def embed_image(self, image: Image.Image) -> torch.Tensor:
        image.close()
        return self.query


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        lahori = unit(1.0, 0.0)
        other = unit(0.2, 0.8)
        self.engine = FixedEngine(
            query=lahori,
            references=[
                ReferenceEmbedding("red-fort", "lahori-gate", lahori),
                ReferenceEmbedding("red-fort", "lahori-gate", unit(0.96, 0.28)),
                ReferenceEmbedding("red-fort", "diwan-i-khas", other),
            ],
        )
        self.client = TestClient(create_app(self.engine))
        self.jpeg = tiny_jpeg()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["modelLoaded"])
        self.assertEqual(body["device"], "cpu")
        self.assertEqual(body["referencePhotographs"], 3)
        self.assertTrue(body["acceptance"]["provisional"])
        self.assertEqual(body["acceptance"]["aggregation"], "max_cosine_per_checkpoint")

    def test_missing_image(self) -> None:
        response = self.client.post("/recognize", data={"siteSlug": "red-fort"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_image")

    def test_empty_image(self) -> None:
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("empty.jpg", b"", "image/jpeg")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["message"].lower())

    def test_invalid_image(self) -> None:
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("notes.txt", b"this is not a photograph", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)
        corrupt = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("broken.jpg", b"\xff\xd8\xff\xd8not-a-jpeg", "image/jpeg")},
        )
        self.assertEqual(corrupt.status_code, 400)
        self.assertEqual(corrupt.json()["code"], "invalid_image")

    def test_unknown_destination(self) -> None:
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "not-a-destination"},
            files={"image": ("photo.jpg", self.jpeg, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")

    def test_image_over_size_limit(self) -> None:
        payload = b"\xff" * (8 * 1024 * 1024 + 1)
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("large.jpg", payload, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 413)

    def test_stored_reference_is_recognized(self) -> None:
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("photo.jpg", self.jpeg, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "match")
        self.assertEqual(body["checkpointId"], "lahori-gate")
        self.assertEqual(body["checkpointName"], "Lahori Gate")
        self.assertGreaterEqual(body["bestSimilarity"], 0.97)
        self.assertGreaterEqual(body["margin"], 0.05)
        self.assertEqual(body["referenceCount"], 2)
        self.assertNotIn("probability", body["explanation"].split("not a probability")[0])
        self.assertNotIn("diwan-i-khas", response.text)

    def test_low_score_is_no_match_without_a_name(self) -> None:
        self.engine.query = unit(0.5, 0.86602540378)
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("photo.jpg", self.jpeg, "image/jpeg")},
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "no_match")
        self.assertIsNone(body["checkpointId"])
        self.assertIsNone(body["checkpointName"])
        self.assertLess(body["bestSimilarity"], 0.97)
        self.assertNotIn("lahori-gate", response.text)
        self.assertNotIn("Lahori", response.text)
        self.assertNotIn("diwan-i-khas", response.text)

    def test_narrow_margin_is_no_match_without_a_runner_up(self) -> None:
        self.engine.query = unit(1.0, 0.0)
        self.engine.references = [
            ReferenceEmbedding("red-fort", "lahori-gate", unit(1.0, 0.0)),
            ReferenceEmbedding("red-fort", "diwan-i-khas", unit(0.98, 0.198997487)),
        ]
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("photo.jpg", self.jpeg, "image/jpeg")},
        )
        body = response.json()
        self.assertEqual(body["status"], "no_match")
        self.assertIsNone(body["checkpointId"])
        self.assertIsNone(body["checkpointName"])
        self.assertLess(body["margin"], 0.05)
        self.assertNotIn("lahori-gate", response.text)
        self.assertNotIn("diwan-i-khas", response.text)
        self.assertNotIn("Diwan", response.text)

    def test_destination_without_references(self) -> None:
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "taj-mahal"},
            files={"image": ("photo.jpg", self.jpeg, "image/jpeg")},
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "no_match")
        self.assertIsNone(body["checkpointId"])
        self.assertIsNone(body["checkpointName"])
        self.assertIn("no reference photographs", body["explanation"])
        self.assertNotIn("Mausoleum", response.text)

    def test_other_destination_references_are_not_used(self) -> None:
        self.engine.references = [
            ReferenceEmbedding("taj-mahal", "taj-mahal-mausoleum", unit(1.0, 0.0)),
        ]
        response = self.client.post(
            "/recognize",
            data={"siteSlug": "red-fort"},
            files={"image": ("photo.jpg", self.jpeg, "image/jpeg")},
        )
        body = response.json()
        self.assertEqual(body["status"], "no_match")
        self.assertIsNone(body["checkpointId"])
        self.assertNotIn("Mausoleum", response.text)


if __name__ == "__main__":
    unittest.main()
