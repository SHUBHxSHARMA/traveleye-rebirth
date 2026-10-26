"""Leave-one-out evaluation of the expanded local reference collection.

Uses the OpenCLIP ViT-B-32 weights already stored in local-recognition/cache.
It does not download photographs or model files, and it does not write
embedding_evaluation.csv.
"""

from __future__ import annotations

import csv
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import torch
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from open_clip.constants import OPENAI_DATASET_MEAN, OPENAI_DATASET_STD

import open_clip

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "reference_manifest.csv"
ORIGINAL_RESULTS = SCRIPT_DIR / "embedding_evaluation.csv"
RESULTS_PATH = SCRIPT_DIR / "expanded_leave_one_out.csv"
SUMMARY_PATH = SCRIPT_DIR / "expanded_leave_one_out_summary.txt"
WEIGHTS = SCRIPT_DIR / "cache" / "models--timm--vit_base_patch32_clip_224.openai" / "snapshots" / "a6f597a30f7b82c51704746581f9a4e41421e878" / "open_clip_model.safetensors"

# A duplicate screen only. It is not a recognition acceptance threshold.
NEAR_DUPLICATE = 0.98


@dataclass
class Photograph:
    collection: str
    destination_slug: str
    checkpoint_id: str
    path: Path
    author: str
    licence: str
    source_page: str
    direct_image_url: str
    licence_url: str
    stored_form: str
    viewpoint: str
    embedding: torch.Tensor | None = None
    error: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.destination_slug, self.checkpoint_id)

    @property
    def label(self) -> str:
        return f"{self.destination_slug}/{self.checkpoint_id}/{self.path.name}"


def cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    return float(torch.dot(left, right).item())


def load_rows() -> list[dict[str, str]]:
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(rows: list[dict[str, str]]) -> tuple[list[Photograph], list[str], list[str]]:
    photos: list[Photograph] = []
    flags: list[str] = []
    excluded: list[str] = []
    required_added = (
        "destination_slug",
        "checkpoint_id",
        "local_path",
        "source_page",
        "direct_image_url",
        "author",
        "licence",
        "licence_url",
    )
    for row in rows:
        collection = row["collection"]
        label = f"{collection} {row['destination_slug']}/{row['checkpoint_id']} {Path(row['local_path']).name if row['local_path'] else '(no file)'}"
        if collection == "shortlist":
            excluded.append(f"{label}: verified shortlist only. No local file was downloaded.")
            continue
        if collection not in {"existing", "added"}:
            excluded.append(f"{label}: unknown collection value {collection!r}.")
            continue
        missing = [field for field in ("destination_slug", "checkpoint_id", "local_path") if not row[field].strip()]
        if collection == "added":
            missing.extend(field for field in required_added if field not in missing and not row[field].strip())
        if missing:
            excluded.append(f"{label}: missing {', '.join(missing)}.")
            continue
        path = Path(row["local_path"])
        if not path.is_file():
            excluded.append(f"{label}: file is not on disk at {path}.")
            continue
        if collection == "existing" and (not row["author"].strip() or not row["licence"].strip()):
            flags.append(
                f"{label}: the project data records no author or licence. "
                "The checkpoint label is kept. No attribution was invented."
            )
        photos.append(
            Photograph(
                collection=collection,
                destination_slug=row["destination_slug"],
                checkpoint_id=row["checkpoint_id"],
                path=path,
                author=row["author"],
                licence=row["licence"],
                source_page=row["source_page"],
                direct_image_url=row["direct_image_url"],
                licence_url=row["licence_url"],
                stored_form=row["stored_form"],
                viewpoint=row["viewpoint"],
            )
        )
    return photos, flags, excluded


def select_device() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        torch.zeros(1, device="cuda")
    except Exception:
        return torch.device("cpu")
    return torch.device("cuda")


def load_model(device: torch.device):
    if not WEIGHTS.is_file():
        raise FileNotFoundError(f"Cached weights not found: {WEIGHTS}")
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
    model.eval()
    return model, preprocess


def embed(model, preprocess, device: torch.device, photos: list[Photograph]) -> None:
    for photo in photos:
        try:
            with Image.open(photo.path) as image:
                tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(device)
            with torch.inference_mode():
                features = model.encode_image(tensor)
                features = F.normalize(features, dim=-1)
            photo.embedding = features.squeeze(0).detach().float().cpu()
            del tensor, features
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            photo.error = str(exc)


def ranked_others(query: Photograph, gallery: list[Photograph]) -> list[tuple[Photograph, float]]:
    return sorted(
        (
            (photo, cosine(query.embedding, photo.embedding))
            for photo in gallery
            if photo is not query and photo.embedding is not None
        ),
        key=lambda item: item[1],
        reverse=True,
    )


def leave_one_out(query: Photograph, gallery: list[Photograph]) -> dict[str, str]:
    ranked = ranked_others(query, gallery)
    siblings = [(photo, score) for photo, score in ranked if photo.key == query.key]
    others = [(photo, score) for photo, score in ranked if photo.key != query.key]
    if not siblings:
        return {
            "evaluable": "no",
            "correct_ranks_above": "",
            "independent_ranks_above": "",
            "best_sibling": "",
            "best_sibling_similarity": "",
            "best_sibling_rank": "",
            "best_other": "",
            "best_other_similarity": "",
            "best_other_rank": "",
            "independent_sibling": "",
            "independent_similarity": "",
            "independent_rank": "",
            "near_duplicate_sibling": "",
            "note": "Only one photograph of this checkpoint is in this gallery.",
        }
    best_sibling, sibling_score = siblings[0]
    sibling_rank = next(rank for rank, (photo, _) in enumerate(ranked, start=1) if photo is best_sibling)
    best_other, other_score = others[0]
    other_rank = next(rank for rank, (photo, _) in enumerate(ranked, start=1) if photo is best_other)
    near = [(photo, score) for photo, score in siblings if score >= NEAR_DUPLICATE]
    independent = [(photo, score) for photo, score in siblings if score < NEAR_DUPLICATE]
    if independent:
        independent_photo, independent_score = independent[0]
        independent_rank = next(
            rank for rank, (photo, _) in enumerate(ranked, start=1) if photo is independent_photo
        )
        independent_above = "yes" if independent_rank < other_rank else "no"
    else:
        independent_photo = None
        independent_score = None
        independent_rank = None
        independent_above = "no-independent-sibling"
    return {
        "evaluable": "yes",
        "correct_ranks_above": "yes" if sibling_rank < other_rank else "no",
        "independent_ranks_above": independent_above,
        "best_sibling": best_sibling.label,
        "best_sibling_similarity": f"{sibling_score:.8f}",
        "best_sibling_rank": str(sibling_rank),
        "best_other": best_other.label,
        "best_other_similarity": f"{other_score:.8f}",
        "best_other_rank": str(other_rank),
        "independent_sibling": independent_photo.label if independent_photo else "",
        "independent_similarity": f"{independent_score:.8f}" if independent_score is not None else "",
        "independent_rank": str(independent_rank) if independent_rank is not None else "",
        "near_duplicate_sibling": near[0][0].label if near else "",
        "note": "",
    }


def write_results(
    valid: list[Photograph],
    same_scores: list[tuple[Photograph, float]],
    cross_pairs: list[tuple[Photograph, Photograph, float]],
    near_pairs: list[tuple[Photograph, Photograph, float]],
    expanded_queries: list[tuple[Photograph, dict[str, str]]],
    original_queries: list[tuple[Photograph, dict[str, str]]],
) -> None:
    fieldnames = [
        "record_type",
        "collection",
        "destination_slug",
        "checkpoint_id",
        "photograph",
        "stored_form",
        "other_destination_slug",
        "other_checkpoint_id",
        "other_photograph",
        "cosine_similarity",
        "rank",
        "same_checkpoint",
        "correct_ranks_above_other_checkpoints",
        "independent_sibling_ranks_above",
        "note",
    ]
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for photo in valid:
            writer.writerow(
                {
                    "record_type": "label",
                    "collection": photo.collection,
                    "destination_slug": photo.destination_slug,
                    "checkpoint_id": photo.checkpoint_id,
                    "photograph": str(photo.path),
                    "stored_form": photo.stored_form,
                    "other_destination_slug": "",
                    "other_checkpoint_id": "",
                    "other_photograph": "",
                    "cosine_similarity": "",
                    "rank": "",
                    "same_checkpoint": "",
                    "correct_ranks_above_other_checkpoints": "",
                    "independent_sibling_ranks_above": "",
                    "note": photo.viewpoint,
                }
            )
        for photo, score in same_scores:
            writer.writerow(
                {
                    "record_type": "same_image",
                    "collection": photo.collection,
                    "destination_slug": photo.destination_slug,
                    "checkpoint_id": photo.checkpoint_id,
                    "photograph": str(photo.path),
                    "stored_form": photo.stored_form,
                    "other_destination_slug": photo.destination_slug,
                    "other_checkpoint_id": photo.checkpoint_id,
                    "other_photograph": str(photo.path),
                    "cosine_similarity": f"{score:.8f}",
                    "rank": "",
                    "same_checkpoint": "yes",
                    "correct_ranks_above_other_checkpoints": "",
                    "independent_sibling_ranks_above": "",
                    "note": "Same embedding compared with itself. This is not recognition accuracy.",
                }
            )
        for left, right, score in near_pairs:
            writer.writerow(
                {
                    "record_type": "near_duplicate",
                    "collection": left.collection,
                    "destination_slug": left.destination_slug,
                    "checkpoint_id": left.checkpoint_id,
                    "photograph": str(left.path),
                    "stored_form": left.stored_form,
                    "other_destination_slug": right.destination_slug,
                    "other_checkpoint_id": right.checkpoint_id,
                    "other_photograph": str(right.path),
                    "cosine_similarity": f"{score:.8f}",
                    "rank": "",
                    "same_checkpoint": "yes" if left.key == right.key else "no",
                    "correct_ranks_above_other_checkpoints": "",
                    "independent_sibling_ranks_above": "",
                    "note": f"Cosine similarity is at least {NEAR_DUPLICATE}. Not treated as an independent viewpoint.",
                }
            )
        for left, right, score in cross_pairs:
            writer.writerow(
                {
                    "record_type": "cross_checkpoint",
                    "collection": left.collection,
                    "destination_slug": left.destination_slug,
                    "checkpoint_id": left.checkpoint_id,
                    "photograph": str(left.path),
                    "stored_form": left.stored_form,
                    "other_destination_slug": right.destination_slug,
                    "other_checkpoint_id": right.checkpoint_id,
                    "other_photograph": str(right.path),
                    "cosine_similarity": f"{score:.8f}",
                    "rank": "",
                    "same_checkpoint": "no",
                    "correct_ranks_above_other_checkpoints": "",
                    "independent_sibling_ranks_above": "",
                    "note": "",
                }
            )
        for scope, queries in (("leave_one_out_expanded", expanded_queries), ("leave_one_out_original_22", original_queries)):
            for photo, result in queries:
                writer.writerow(
                    {
                        "record_type": scope,
                        "collection": photo.collection,
                        "destination_slug": photo.destination_slug,
                        "checkpoint_id": photo.checkpoint_id,
                        "photograph": str(photo.path),
                        "stored_form": photo.stored_form,
                        "other_destination_slug": "",
                        "other_checkpoint_id": "",
                        "other_photograph": result["best_sibling"],
                        "cosine_similarity": result["best_sibling_similarity"],
                        "rank": result["best_sibling_rank"],
                        "same_checkpoint": "yes" if result["best_sibling"] else "",
                        "correct_ranks_above_other_checkpoints": result["correct_ranks_above"],
                        "independent_sibling_ranks_above": result["independent_ranks_above"],
                        "note": (
                            f"Nearest other checkpoint: {result['best_other']} "
                            f"rank {result['best_other_rank']} similarity {result['best_other_similarity']}. "
                            f"Independent sibling: {result['independent_sibling'] or 'none'} "
                            f"rank {result['independent_rank']} similarity {result['independent_similarity']}. "
                            f"{result['note']}"
                        ).strip(),
                    }
                )


def count_outcomes(queries: list[tuple[Photograph, dict[str, str]]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for _, result in queries:
        if result["evaluable"] != "yes":
            counts["not_evaluable"] += 1
            continue
        counts["evaluable"] += 1
        counts[f"raw_{result['correct_ranks_above']}"] += 1
        counts[f"independent_{result['independent_ranks_above']}"] += 1
    return counts


def by_checkpoint(queries: list[tuple[Photograph, dict[str, str]]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for photo, result in queries:
        grouped[photo.key].append(result)
    return grouped


def format_counts(counts: dict[str, int]) -> str:
    return (
        f"evaluable queries {counts['evaluable']}, "
        f"raw sibling ranked above other checkpoints {counts['raw_yes']}/{counts['evaluable'] or 0}, "
        f"independent sibling ranked above {counts['independent_yes']}, "
        f"independent sibling did not {counts['independent_no']}, "
        f"no independent sibling {counts['independent_no-independent-sibling']}, "
        f"not evaluable {counts['not_evaluable']}"
    )


def main() -> int:
    if not ORIGINAL_RESULTS.is_file():
        print(f"Original results are missing: {ORIGINAL_RESULTS}")
        return 1
    started = time.perf_counter()
    rows = load_rows()
    photos, flags, excluded = audit(rows)
    device = select_device()
    model, preprocess = load_model(device)
    embed_started = time.perf_counter()
    embed(model, preprocess, device, photos)
    embed_seconds = time.perf_counter() - embed_started

    valid = [photo for photo in photos if photo.embedding is not None]
    for photo in photos:
        if photo.embedding is None:
            excluded.append(f"{photo.label}: unreadable ({photo.error}).")

    original = [photo for photo in valid if photo.collection == "existing"]
    added = [photo for photo in valid if photo.collection == "added"]
    same_scores = [(photo, cosine(photo.embedding, photo.embedding)) for photo in valid]

    cross_pairs: list[tuple[Photograph, Photograph, float]] = []
    near_pairs: list[tuple[Photograph, Photograph, float]] = []
    for index, left in enumerate(valid):
        for right in valid[index + 1 :]:
            score = cosine(left.embedding, right.embedding)
            if left.key != right.key:
                cross_pairs.append((left, right, score))
            elif score >= NEAR_DUPLICATE:
                near_pairs.append((left, right, score))
    cross_pairs.sort(key=lambda item: item[2], reverse=True)
    near_pairs.sort(key=lambda item: item[2], reverse=True)

    expanded_queries = [(photo, leave_one_out(photo, valid)) for photo in valid]
    original_queries = [(photo, leave_one_out(photo, original)) for photo in original]
    write_results(valid, same_scores, cross_pairs, near_pairs, expanded_queries, original_queries)

    expanded_counts = count_outcomes(expanded_queries)
    original_counts = count_outcomes(original_queries)
    expanded_by_key = by_checkpoint(expanded_queries)
    original_by_key = by_checkpoint(original_queries)
    counts: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"existing": 0, "added": 0})
    for photo in valid:
        counts[photo.key][photo.collection] += 1

    lines = [
        "Expanded OpenCLIP ViT-B-32 leave-one-out evaluation",
        "Weights: cached open_clip_model.safetensors. No download was requested.",
        f"Device: {device}" + (f" ({torch.cuda.get_device_name(device)})" if device.type == "cuda" else ""),
        f"Valid photographs: {len(valid)} ({len(original)} original, {len(added)} additional)",
        f"Checkpoints represented: {len(counts)}",
        f"Embedding dimensions: {int(valid[0].embedding.shape[0]) if valid else 0}",
        f"Embedding time: {embed_seconds:.2f} s",
        f"Total time: {time.perf_counter() - started:.2f} s",
        f"Same-image similarity: {min(score for _, score in same_scores):.6f} to {max(score for _, score in same_scores):.6f}",
        "Same-image similarity only shows that a vector matches itself.",
        f"Near-duplicate screen: cosine similarity >= {NEAR_DUPLICATE}. This is not an acceptance threshold.",
        "",
        "Metadata flags",
    ]
    lines.extend(flags or ["None."])
    lines.extend(["", "Excluded"])
    lines.extend(excluded or ["None."])
    lines.extend(["", "Photographs by checkpoint"])
    for key in sorted(counts):
        slug, checkpoint_id = key
        existing_count = counts[key]["existing"]
        added_count = counts[key]["added"]
        lines.append(f"{slug}/{checkpoint_id}: {existing_count} original, {added_count} additional")

    lines.extend(["", "Near-duplicate pairs"])
    if near_pairs:
        for left, right, score in near_pairs:
            lines.append(f"{score:.4f}  {left.label}  vs  {right.label}")
    else:
        lines.append("None at the duplicate screen.")

    lines.extend(["", "Highest different-checkpoint pairs"])
    lines.append("No acceptance threshold is proposed.")
    for left, right, score in cross_pairs[:10]:
        lines.append(f"{score:.4f}  {left.label}  vs  {right.label}")

    lines.extend(
        [
            "",
            "Leave-one-out on the original 22 photographs only",
            format_counts(original_counts),
            "",
            "Leave-one-out on the expanded collection",
            format_counts(expanded_counts),
            "",
            "Checkpoints that previously had one photograph",
        ]
    )
    for key in sorted(counts):
        if counts[key]["existing"] != 1:
            continue
        slug, checkpoint_id = key
        if counts[key]["added"] == 0:
            lines.append(f"{slug}/{checkpoint_id}: still one photograph. A new viewpoint cannot be tested.")
            continue
        before = original_by_key[key]
        after = expanded_by_key[key]
        lines.append(
            f"{slug}/{checkpoint_id}: before expansion, the single original photograph had no sibling. "
            f"After expansion, {sum(item['correct_ranks_above'] == 'yes' for item in after)}/"
            f"{len(after)} queries have another photograph of this checkpoint ranked above other checkpoints."
        )
        for photo, result in expanded_queries:
            if photo.key != key:
                continue
            lines.append(
                f"  {photo.path.name}: raw {result['correct_ranks_above'] or 'not evaluable'}, "
                f"independent {result['independent_ranks_above'] or 'not evaluable'}, "
                f"sibling {result['best_sibling_similarity']} rank {result['best_sibling_rank']}, "
                f"other {result['best_other_similarity']} rank {result['best_other_rank']}"
            )
        del before

    lines.extend(["", "Checkpoints that had no original photograph"])
    for key in sorted(counts):
        if counts[key]["existing"] != 0:
            continue
        slug, checkpoint_id = key
        after = expanded_by_key[key]
        evaluable = [item for item in after if item["evaluable"] == "yes"]
        if not evaluable:
            lines.append(f"{slug}/{checkpoint_id}: still too few photographs for leave-one-out.")
            continue
        yes = sum(item["correct_ranks_above"] == "yes" for item in evaluable)
        lines.append(
            f"{slug}/{checkpoint_id}: {yes}/{len(evaluable)} queries have another photograph "
            "of this checkpoint ranked above other checkpoints."
        )
        for photo, result in expanded_queries:
            if photo.key != key:
                continue
            lines.append(
                f"  {photo.path.name}: raw {result['correct_ranks_above'] or 'not evaluable'}, "
                f"independent {result['independent_ranks_above'] or 'not evaluable'}, "
                f"sibling {result['best_sibling_similarity']} rank {result['best_sibling_rank']}, "
                f"other {result['best_other_similarity']} rank {result['best_other_rank']}"
            )

    lines.extend(["", "Checkpoints that already had more than one original photograph"])
    for key in sorted(counts):
        if counts[key]["existing"] < 2:
            continue
        slug, checkpoint_id = key
        before = [item for item in original_by_key[key] if item["evaluable"] == "yes"]
        after = [item for item in expanded_by_key[key] if item["evaluable"] == "yes"]
        before_yes = sum(item["correct_ranks_above"] == "yes" for item in before)
        after_yes = sum(item["correct_ranks_above"] == "yes" for item in after)
        lines.append(
            f"{slug}/{checkpoint_id}: original gallery {before_yes}/{len(before)}; "
            f"expanded gallery {after_yes}/{len(after)}."
        )

    lines.extend(
        [
            "",
            "Limitations",
            "Every query is another stored reference photograph, not a newly captured visitor photograph.",
            "A different file is not automatically an unseen viewpoint. Near-duplicate pairs are listed above.",
            "The viewpoint notes in reference_manifest.csv describe the documented angle. They were not inferred further.",
            "Checkpoints with one photograph still cannot support a leave-one-out test.",
            "The original embedding_evaluation.csv was not modified.",
            f"Detailed rows: {RESULTS_PATH}",
        ]
    )
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
