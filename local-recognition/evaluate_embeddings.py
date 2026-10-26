"""Compare OpenCLIP ViT-B-32 embeddings of the existing Travel Eye reference photographs.

The first run downloads the public OpenAI CLIP ViT-B-32 weights into
local-recognition/cache. OpenCLIP loads that checkpoint from a public file.
The download happens once and is not a paid API call. No language model is
downloaded, and nothing in the Next.js application is changed.

The photograph list starts with the original 22 checkpoint references.
Additional photographs come from reference_manifest.csv when their collection
is "added". The original embedding_evaluation.csv is not overwritten.
public/references/delhi-fort.jpg is the homepage image and is not included.
"""

from __future__ import annotations

import csv
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "cache"
RESULTS_PATH = SCRIPT_DIR / "embedding_evaluation_expanded.csv"
MANIFEST_PATH = SCRIPT_DIR / "reference_manifest.csv"
REFERENCE_DIR = (
    SCRIPT_DIR.parent
    / "Travel_Eye-main (1)"
    / "Travel_Eye-main"
    / "travel-eye"
    / "public"
    / "references"
)

MODEL_NAME = "ViT-B-32"
PRETRAINED = "openai"
TOP_PAIRS = 10

# Deduplicated checkpoint references from src/lib/data/*.ts.
# referenceImageUrl is already included in each referenceImageUrls list.
REFERENCES: list[tuple[str, str, str]] = [
    ("red-fort", "lahori-gate", "lahori-gate.jpg"),
    ("red-fort", "lahori-gate", "lahori-gate-user.jpg"),
    ("red-fort", "chhatta-chowk", "chhatta-chowk.jpg"),
    ("red-fort", "naubat-khana", "naubat-khana.jpg"),
    ("red-fort", "diwan-i-am", "diwan-i-am.jpg"),
    ("red-fort", "diwan-i-khas", "diwan-i-khas-1.jpg"),
    ("red-fort", "diwan-i-khas", "diwan-i-khas-2.jpg"),
    ("red-fort", "diwan-i-khas", "diwan-i-khas-3.jpg"),
    ("red-fort", "mumtaz-mahal", "mumtaz-mahal.jpg"),
    ("red-fort", "rang-mahal", "rang-mahal.jpg"),
    ("red-fort", "rang-mahal", "rang-mahal-user.jpg"),
    ("red-fort", "rang-mahal", "rang-mahal-2.jpg"),
    ("red-fort", "moti-masjid", "moti-masjid-1.jpg"),
    ("red-fort", "moti-masjid", "moti-masjid-2.jpg"),
    ("red-fort", "hammam", "hammam.jpg"),
    ("red-fort", "shahi-burj", "shahi-burj.jpg"),
    ("taj-mahal", "taj-mahal-mausoleum", "taj-mahal.jpg"),
    ("qutub-minar", "qutub-minar-tower", "qutb-minar.jpg"),
    ("qutub-minar", "qutub-iron-pillar", "iron-pillar-delhi.jpg"),
    ("qutub-minar", "qutub-alai-darwaza", "alai-darwaza.jpg"),
    ("sanchi-stupa", "sanchi-great-stupa", "sanchi-stupa-1.jpg"),
    ("khajuraho", "khajuraho-kandariya", "kandariya-mahadeva.jpg"),
]


@dataclass
class Photograph:
    destination_slug: str
    checkpoint_id: str
    path: Path
    embedding: torch.Tensor | None = None
    error: str = ""


def select_device() -> torch.device:
    if not torch.cuda.is_available():
        print("CUDA is not available. Using CPU.")
        return torch.device("cpu")
    try:
        torch.zeros(1, device="cuda")
        return torch.device("cuda")
    except Exception as exc:
        print(f"CUDA could not be initialized ({exc}). Using CPU.")
        return torch.device("cpu")


def memory_line(device: torch.device, label: str) -> str:
    if device.type != "cuda":
        return f"{label}: CUDA not active"
    torch.cuda.synchronize()
    allocated = torch.cuda.memory_allocated(device) / (1024**2)
    reserved = torch.cuda.memory_reserved(device) / (1024**2)
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    return (
        f"{label}: allocated {allocated:.1f} MiB, reserved {reserved:.1f} MiB, "
        f"free {free_bytes / (1024**2):.1f} MiB of {total_bytes / (1024**2):.1f} MiB"
    )


def load_model(device: torch.device):
    import open_clip

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(
        "Loading OpenCLIP ViT-B-32 with the public OpenAI CLIP weights. "
        "If the checkpoint is not already in local-recognition/cache, "
        "this downloads that file once. It is not a paid API call."
    )
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=device,
        cache_dir=str(CACHE_DIR),
        # The public OpenAI ViT-B-32 checkpoint was trained with QuickGELU.
        force_quick_gelu=True,
    )
    model.eval()
    return model, preprocess


def embed_photographs(model, preprocess, device: torch.device, photos: list[Photograph]) -> None:
    for photo in photos:
        if not photo.path.is_file():
            photo.error = "file not found"
            print(f"Unreadable: {photo.path.name} ({photo.error})")
            continue
        try:
            with Image.open(photo.path) as image:
                rgb = image.convert("RGB")
                tensor = preprocess(rgb).unsqueeze(0).to(device)
            with torch.inference_mode():
                features = model.encode_image(tensor)
                features = F.normalize(features, dim=-1)
            photo.embedding = features.squeeze(0).detach().float().cpu()
            del tensor, features
            if device.type == "cuda":
                torch.cuda.empty_cache()
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            photo.error = str(exc)
            print(f"Unreadable: {photo.path.name} ({photo.error})")


def cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    return float(torch.dot(left, right).item())


def write_results(
    photos: list[Photograph],
    same_scores: list[tuple[Photograph, float]],
    cross_pairs: list[tuple[Photograph, Photograph, float]],
    retrieval_rows: list[dict[str, str]],
) -> None:
    fieldnames = [
        "record_type",
        "destination_slug",
        "checkpoint_id",
        "photograph",
        "other_destination_slug",
        "other_checkpoint_id",
        "other_photograph",
        "cosine_similarity",
        "rank",
        "same_checkpoint",
        "note",
    ]
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for photo in photos:
            if photo.embedding is None:
                writer.writerow(
                    {
                        "record_type": "unreadable",
                        "destination_slug": photo.destination_slug,
                        "checkpoint_id": photo.checkpoint_id,
                        "photograph": str(photo.path),
                        "other_destination_slug": "",
                        "other_checkpoint_id": "",
                        "other_photograph": "",
                        "cosine_similarity": "",
                        "rank": "",
                        "same_checkpoint": "",
                        "note": photo.error,
                    }
                )
        for photo, score in same_scores:
            writer.writerow(
                {
                    "record_type": "same_image",
                    "destination_slug": photo.destination_slug,
                    "checkpoint_id": photo.checkpoint_id,
                    "photograph": str(photo.path),
                    "other_destination_slug": photo.destination_slug,
                    "other_checkpoint_id": photo.checkpoint_id,
                    "other_photograph": str(photo.path),
                    "cosine_similarity": f"{score:.8f}",
                    "rank": "",
                    "same_checkpoint": "yes",
                    "note": "comparison with the same embedding",
                }
            )
        for left, right, score in cross_pairs:
            writer.writerow(
                {
                    "record_type": "cross_checkpoint",
                    "destination_slug": left.destination_slug,
                    "checkpoint_id": left.checkpoint_id,
                    "photograph": str(left.path),
                    "other_destination_slug": right.destination_slug,
                    "other_checkpoint_id": right.checkpoint_id,
                    "other_photograph": str(right.path),
                    "cosine_similarity": f"{score:.8f}",
                    "rank": "",
                    "same_checkpoint": "no",
                    "note": "",
                }
            )
        for row in retrieval_rows:
            writer.writerow(row)


def main() -> int:
    started = time.perf_counter()
    if not REFERENCE_DIR.is_dir():
        print(f"Reference directory not found: {REFERENCE_DIR}")
        return 1

    photos = [
        Photograph(slug, checkpoint_id, REFERENCE_DIR / filename)
        for slug, checkpoint_id, filename in REFERENCES
    ]
    if MANIFEST_PATH.is_file():
        with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["collection"] != "added" or not row["local_path"]:
                    continue
                photos.append(
                    Photograph(row["destination_slug"], row["checkpoint_id"], Path(row["local_path"]))
                )
    print(f"Photographs labeled for evaluation: {len(photos)}")
    print("Results are written to embedding_evaluation_expanded.csv.")
    print("embedding_evaluation.csv, the original 22-image run, is left unchanged.")
    device = select_device()
    print(f"Selected device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(device)}")

    try:
        model, preprocess = load_model(device)
    except Exception as exc:
        print("The pretrained model could not be downloaded or loaded.")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1

    print(memory_line(device, "GPU memory before embedding generation"))
    embed_started = time.perf_counter()
    embed_photographs(model, preprocess, device, photos)
    embed_seconds = time.perf_counter() - embed_started
    print(memory_line(device, "GPU memory after embedding generation"))

    valid = [photo for photo in photos if photo.embedding is not None]
    unreadable = [photo for photo in photos if photo.embedding is None]
    if not valid:
        print("No reference photographs could be embedded.")
        write_results(photos, [], [], [])
        return 1

    dimensions = int(valid[0].embedding.shape[0])
    same_scores = [(photo, cosine(photo.embedding, photo.embedding)) for photo in valid]

    cross_pairs: list[tuple[Photograph, Photograph, float]] = []
    for index, left in enumerate(valid):
        for right in valid[index + 1 :]:
            if left.checkpoint_id == right.checkpoint_id and left.destination_slug == right.destination_slug:
                continue
            cross_pairs.append((left, right, cosine(left.embedding, right.embedding)))
    cross_pairs.sort(key=lambda item: item[2], reverse=True)

    retrieval_rows: list[dict[str, str]] = []
    retrieval_summaries: list[str] = []
    counts: dict[tuple[str, str], int] = {}
    for photo in valid:
        counts[(photo.destination_slug, photo.checkpoint_id)] = (
            counts.get((photo.destination_slug, photo.checkpoint_id), 0) + 1
        )

    for query in valid:
        others = [photo for photo in valid if photo is not query]
        ranked = sorted(
            ((photo, cosine(query.embedding, photo.embedding)) for photo in others),
            key=lambda item: item[1],
            reverse=True,
        )
        siblings = [
            (photo, score)
            for photo, score in ranked
            if photo.destination_slug == query.destination_slug
            and photo.checkpoint_id == query.checkpoint_id
        ]
        unrelated = [
            (photo, score)
            for photo, score in ranked
            if not (
                photo.destination_slug == query.destination_slug
                and photo.checkpoint_id == query.checkpoint_id
            )
        ]
        key = (query.destination_slug, query.checkpoint_id)
        if counts[key] < 2:
            retrieval_summaries.append(
                f"{query.destination_slug}/{query.checkpoint_id} ({query.path.name}): "
                "only one reference photograph. This dataset cannot evaluate recognition "
                "from a new viewpoint for this checkpoint."
            )
        else:
            best_sibling, sibling_score = siblings[0]
            sibling_rank = next(
                rank for rank, (photo, _) in enumerate(ranked, start=1) if photo is best_sibling
            )
            best_other, other_score = unrelated[0]
            other_rank = next(
                rank for rank, (photo, _) in enumerate(ranked, start=1) if photo is best_other
            )
            ahead = sibling_rank < other_rank
            retrieval_summaries.append(
                f"{query.destination_slug}/{query.checkpoint_id} ({query.path.name}): "
                f"nearest same-checkpoint photo is {best_sibling.path.name} "
                f"(rank {sibling_rank}, similarity {sibling_score:.4f}); "
                f"nearest other checkpoint is {best_other.destination_slug}/{best_other.checkpoint_id} "
                f"{best_other.path.name} (rank {other_rank}, similarity {other_score:.4f}); "
                f"same-checkpoint photo ranks above unrelated checkpoints: {'yes' if ahead else 'no'}."
            )
        for rank, (photo, score) in enumerate(ranked, start=1):
            same_checkpoint = (
                photo.destination_slug == query.destination_slug
                and photo.checkpoint_id == query.checkpoint_id
            )
            retrieval_rows.append(
                {
                    "record_type": "retrieval",
                    "destination_slug": query.destination_slug,
                    "checkpoint_id": query.checkpoint_id,
                    "photograph": str(query.path),
                    "other_destination_slug": photo.destination_slug,
                    "other_checkpoint_id": photo.checkpoint_id,
                    "other_photograph": str(photo.path),
                    "cosine_similarity": f"{score:.8f}",
                    "rank": str(rank),
                    "same_checkpoint": "yes" if same_checkpoint else "no",
                    "note": "",
                }
            )

    write_results(photos, same_scores, cross_pairs, retrieval_rows)
    total_seconds = time.perf_counter() - started
    same_min = min(score for _, score in same_scores)
    same_max = max(score for _, score in same_scores)

    print()
    print(f"Model: OpenCLIP {MODEL_NAME} ({PRETRAINED})")
    print(f"Selected device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(device)}")
    print(f"Valid reference photographs: {len(valid)}")
    print(f"Unreadable photographs: {len(unreadable)}")
    print(f"Embedding dimensions: {dimensions}")
    print(f"Embedding time: {embed_seconds:.2f} s")
    print(f"Total processing time: {total_seconds:.2f} s")
    print(f"Results: {RESULTS_PATH}")
    print()
    print("Same-image comparison")
    print(f"Similarity range: {same_min:.6f} to {same_max:.6f}")
    print(
        "A score near 1.0 only confirms that an embedding matches itself. "
        "It does not measure recognition of a new visitor photograph."
    )
    print()
    print(f"Most similar different-checkpoint pairs (top {TOP_PAIRS})")
    print("No acceptance threshold is proposed.")
    for left, right, score in cross_pairs[:TOP_PAIRS]:
        print(
            f"{score:.4f}  {left.destination_slug}/{left.checkpoint_id}/{left.path.name}"
            f"  vs  {right.destination_slug}/{right.checkpoint_id}/{right.path.name}"
        )
    print()
    print("Retrieval")
    for line in retrieval_summaries:
        print(line)
    print()
    print("Dataset limitations")
    single = sorted(key for key, count in counts.items() if count == 1)
    multi = sorted(key for key, count in counts.items() if count > 1)
    print(
        "Checkpoints with more than one photograph, where another view can be ranked: "
        + ", ".join(f"{slug}/{checkpoint_id}" for slug, checkpoint_id in multi)
    )
    print(
        "Checkpoints with one photograph. This dataset cannot evaluate a new viewpoint: "
        + ", ".join(f"{slug}/{checkpoint_id}" for slug, checkpoint_id in single)
    )
    if unreadable:
        print("Unreadable photographs:")
        for photo in unreadable:
            print(f"  {photo.path} ({photo.error})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
