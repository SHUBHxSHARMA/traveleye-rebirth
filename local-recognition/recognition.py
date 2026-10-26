"""In-memory OpenCLIP matching for one destination at a time.

Reference embeddings are computed once at startup and kept on CPU.
They are not written to disk, and the evaluation CSV files are not opened.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import torch
import torch.nn.functional as F
from PIL import Image
from open_clip.constants import OPENAI_DATASET_MEAN, OPENAI_DATASET_STD

import open_clip

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "reference_manifest.csv"
WEIGHTS = (
    SCRIPT_DIR
    / "cache"
    / "models--timm--vit_base_patch32_clip_224.openai"
    / "snapshots"
    / "a6f597a30f7b82c51704746581f9a4e41421e878"
    / "open_clip_model.safetensors"
)

# Provisional development defaults. They are intentionally strict so an
# uncertain comparison returns no_match. They have not been calibrated on
# separate visitor photographs. Override them with TRAVELEYE_MIN_SIMILARITY
# and TRAVELEYE_MIN_MARGIN. Neither value is a probability.
DEFAULT_MIN_SIMILARITY = 0.97
DEFAULT_MIN_MARGIN = 0.05
MAX_PIXELS = 48_000_000

# Checkpoint ids and display names are copied from src/lib/data.
# This service does not add destinations or checkpoints.
DESTINATIONS: dict[str, dict[str, str]] = {
    "red-fort": {
        "lahori-gate": "Lahori Gate",
        "chhatta-chowk": "Chhatta Chowk",
        "naubat-khana": "Naubat Khana (Drum House)",
        "diwan-i-am": "Diwan-i-Am (Hall of Public Audience)",
        "diwan-i-khas": "Diwan-i-Khas (Hall of Private Audience)",
        "mumtaz-mahal": "Mumtaz Mahal",
        "rang-mahal": "Rang Mahal (Palace of Colours)",
        "moti-masjid": "Moti Masjid (Pearl Mosque)",
        "hammam": "Royal Hammam (Baths)",
        "shahi-burj": "Shahi Burj (Royal Tower)",
    },
    "taj-mahal": {
        "taj-mahal-mausoleum": "Mausoleum",
        "taj-mahal-gateway": "Great Gate",
        "taj-mahal-charbagh": "Charbagh",
        "taj-mahal-mosque": "Mosque and jawab",
    },
    "qutub-minar": {
        "qutub-minar-tower": "Qutub Minar",
        "qutub-iron-pillar": "Iron pillar",
        "qutub-alai-darwaza": "Alai Darwaza",
        "qutub-quwwat-ul-islam": "Quwwat-ul-Islam mosque",
    },
    "sanchi-stupa": {
        "sanchi-great-stupa": "Great Stupa",
        "sanchi-toranas": "Gateways",
        "sanchi-ashokan-pillar": "Ashokan pillar",
        "sanchi-stupa-3": "Stupa 3",
    },
    "khajuraho": {
        "khajuraho-kandariya": "Kandariya Mahadeva Temple",
        "khajuraho-lakshmana": "Lakshmana Temple",
        "khajuraho-vishvanatha": "Vishvanatha Temple",
        "khajuraho-parshvanatha": "Parshvanatha Temple",
    },
}


@dataclass
class ReferenceEmbedding:
    destination_slug: str
    checkpoint_id: str
    embedding: torch.Tensor


@dataclass
class RankedCheckpoint:
    checkpoint_id: str
    name: str
    score: float
    reference_count: int


def read_limit(name: str, default: float, low: float, high: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number. The service did not start.") from exc
    if not low <= value <= high:
        raise RuntimeError(f"{name} must be between {low} and {high}. The service did not start.")
    return value


def checkpoint_name(destination_slug: str, checkpoint_id: str) -> str | None:
    return DESTINATIONS.get(destination_slug, {}).get(checkpoint_id)


def select_device() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        torch.zeros(1, device="cuda")
    except Exception:
        return torch.device("cpu")
    return torch.device("cuda")


def load_manifest_rows() -> list[dict[str, str]]:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Reference manifest is missing: {MANIFEST_PATH}. The service did not start."
        )
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class RecognitionEngine:
    """One loaded model and an in-memory table of normalized reference embeddings."""

    def __init__(
        self,
        device: torch.device,
        model: torch.nn.Module | None,
        preprocess,
        references: list[ReferenceEmbedding],
        min_similarity: float,
        min_margin: float,
    ) -> None:
        self.device = device
        self.model = model
        self.preprocess = preprocess
        self.references = references
        self.min_similarity = min_similarity
        self.min_margin = min_margin
        if model is not None:
            model.eval()

    @classmethod
    def load(cls) -> RecognitionEngine:
        if not WEIGHTS.is_file():
            raise FileNotFoundError(
                "The cached OpenCLIP ViT-B-32 weights are missing at "
                f"{WEIGHTS}. The service will not download them."
            )
        min_similarity = read_limit("TRAVELEYE_MIN_SIMILARITY", DEFAULT_MIN_SIMILARITY, 0.0, 1.0)
        min_margin = read_limit("TRAVELEYE_MIN_MARGIN", DEFAULT_MIN_MARGIN, 0.0, 1.0)
        device = select_device()
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained=str(WEIGHTS),
            device=device,
            force_quick_gelu=True,
            image_mean=OPENAI_DATASET_MEAN,
            image_std=OPENAI_DATASET_STD,
            image_interpolation="bicubic",
            image_resize_mode="shortest",
        )
        engine = cls(device, model, preprocess, [], min_similarity, min_margin)
        references, skipped = engine._embed_references()
        if not references:
            raise RuntimeError("No reference photographs could be embedded. The service did not start.")
        engine.references = references
        if device.type == "cuda":
            torch.cuda.empty_cache()
        print(
            f"Cached {len(references)} reference embeddings in memory on {device.type}. "
            f"Skipped {skipped}. Nothing was written to disk.",
            flush=True,
        )
        return engine

    def _embed_references(self) -> tuple[list[ReferenceEmbedding], int]:
        references: list[ReferenceEmbedding] = []
        skipped = 0
        for row in load_manifest_rows():
            if row.get("collection") not in {"existing", "added"}:
                skipped += 1
                continue
            destination_slug = row.get("destination_slug", "").strip()
            checkpoint_id = row.get("checkpoint_id", "").strip()
            local_path = row.get("local_path", "").strip()
            if checkpoint_name(destination_slug, checkpoint_id) is None or not local_path:
                skipped += 1
                continue
            path = Path(local_path)
            if not path.is_file():
                skipped += 1
                continue
            try:
                with Image.open(path) as image:
                    image.load()
                    vector = self.embed_image(image)
            except (OSError, ValueError):
                skipped += 1
                continue
            references.append(
                ReferenceEmbedding(destination_slug, checkpoint_id, vector)
            )
        return references, skipped

    def embed_image(self, image: Image.Image) -> torch.Tensor:
        if self.model is None or self.preprocess is None:
            raise RuntimeError("The recognition model is not loaded.")
        tensor = self.preprocess(image.convert("RGB")).unsqueeze(0).to(self.device)
        features = None
        try:
            with torch.inference_mode():
                features = self.model.encode_image(tensor)
                features = F.normalize(features, dim=-1)
                return features.squeeze(0).detach().float().cpu()
        finally:
            del tensor
            if features is not None:
                del features

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "modelLoaded": self.model is not None,
            "device": self.device.type,
            "referencePhotographs": len(self.references),
            "acceptance": {
                "minSimilarity": self.min_similarity,
                "minMargin": self.min_margin,
                "provisional": True,
                "aggregation": "max_cosine_per_checkpoint",
            },
        }

    def match(self, destination_slug: str, query: torch.Tensor) -> dict[str, object]:
        grouped: dict[str, list[float]] = {}
        for reference in self.references:
            if reference.destination_slug != destination_slug:
                continue
            name = checkpoint_name(destination_slug, reference.checkpoint_id)
            if name is None:
                continue
            grouped.setdefault(reference.checkpoint_id, []).append(
                float(torch.dot(query, reference.embedding).item())
            )
        if not grouped:
            return no_reference_result()

        ranked = [
            RankedCheckpoint(
                checkpoint_id=checkpoint_id,
                name=checkpoint_name(destination_slug, checkpoint_id) or "",
                score=max(similarities),
                reference_count=len(similarities),
            )
            for checkpoint_id, similarities in grouped.items()
        ]
        ranked.sort(key=lambda item: item.score, reverse=True)
        best = ranked[0]
        margin = None if len(ranked) == 1 else best.score - ranked[1].score
        score_ok = best.score >= self.min_similarity
        margin_ok = margin is None or margin >= self.min_margin
        if not score_ok or not margin_ok:
            reason = "margin" if score_ok else "similarity"
            return no_match_result(best.score, margin, reason)
        return {
            "status": "match",
            "code": "match",
            "checkpointId": best.checkpoint_id,
            "checkpointName": best.name,
            "bestSimilarity": round(best.score, 6),
            "margin": None if margin is None else round(margin, 6),
            "referenceCount": best.reference_count,
            "explanation": match_explanation(margin is None),
        }


def no_reference_result() -> dict[str, object]:
    return {
        "status": "no_match",
        "code": "no_match",
        "checkpointId": None,
        "checkpointName": None,
        "bestSimilarity": None,
        "margin": None,
        "referenceCount": None,
        "explanation": (
            "No reliable match found. This destination has no reference photographs, "
            "so no checkpoint can be recognized."
        ),
    }


def no_match_result(score: float, margin: float | None, reason: str) -> dict[str, object]:
    if reason == "margin":
        detail = "The leading checkpoint is not far enough ahead of the next one under the provisional acceptance checks."
    else:
        detail = "The closest stored photograph is not close enough under the provisional acceptance checks."
    return {
        "status": "no_match",
        "code": "no_match",
        "checkpointId": None,
        "checkpointName": None,
        "bestSimilarity": round(score, 6),
        "margin": None if margin is None else round(margin, 6),
        "referenceCount": None,
        "explanation": (
            f"No reliable match found. {detail} "
            "The similarity score is a cosine comparison, not a probability."
        ),
    }


def match_explanation(only_checkpoint: bool) -> str:
    if only_checkpoint:
        lead = (
            "The photograph is close to the stored references for this checkpoint. "
            "No other checkpoint at this destination has reference photographs to compare."
        )
    else:
        lead = (
            "The photograph is close to the stored references for this checkpoint "
            "and clearly ahead of the other checkpoints at this destination."
        )
    return f"{lead} The similarity score is a cosine comparison, not a probability."
