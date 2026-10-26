"""Audit the provisional 0.97 / 0.05 acceptance rules on held-out reference photographs.

The query photograph is removed from the reference gallery before scoring.
A photograph compared with itself is recorded only as a sanity check and is
not counted as recognition. This script does not change production thresholds,
photographs, or the existing evaluation CSV files.
"""

from __future__ import annotations

import csv
import hashlib
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
from recognition import DEFAULT_MIN_MARGIN, DEFAULT_MIN_SIMILARITY

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "reference_manifest.csv"
RESULTS_PATH = SCRIPT_DIR / "acceptance_audit.csv"
REPORT_PATH = SCRIPT_DIR / "acceptance_audit_report.txt"
WEIGHTS = (
    SCRIPT_DIR
    / "cache"
    / "models--timm--vit_base_patch32_clip_224.openai"
    / "snapshots"
    / "a6f597a30f7b82c51704746581f9a4e41421e878"
    / "open_clip_model.safetensors"
)

# Same screen used by the earlier expanded evaluation. It flags leakage.
# It is not an acceptance threshold and it is not written back to the service.
NEAR_DUPLICATE = 0.98
MIN_SIMILARITY = DEFAULT_MIN_SIMILARITY
MIN_MARGIN = DEFAULT_MIN_MARGIN


@dataclass
class Photograph:
    collection: str
    destination_slug: str
    checkpoint_id: str
    path: Path
    viewpoint: str
    sha256: str
    embedding: torch.Tensor | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.destination_slug, self.checkpoint_id)

    @property
    def label(self) -> str:
        return f"{self.destination_slug}/{self.checkpoint_id}/{self.path.name}"


def cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    return float(torch.dot(left, right).item())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_photos() -> tuple[list[Photograph], list[str]]:
    photos: list[Photograph] = []
    notes: list[str] = []
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["collection"] not in {"existing", "added"}:
            notes.append(f"Excluded {row['collection']} {row['destination_slug']}/{row['checkpoint_id']}: no local file.")
            continue
        path = Path(row["local_path"])
        if not path.is_file():
            notes.append(f"Excluded missing file {row['destination_slug']}/{row['checkpoint_id']}.")
            continue
        photos.append(
            Photograph(
                collection=row["collection"],
                destination_slug=row["destination_slug"],
                checkpoint_id=row["checkpoint_id"],
                path=path,
                viewpoint=row["viewpoint"],
                sha256=file_sha256(path),
            )
        )
    return photos, notes


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
        raise FileNotFoundError(f"Cached weights are missing: {WEIGHTS}")
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


def embed(model, preprocess, device: torch.device, photos: list[Photograph]) -> list[str]:
    failed: list[str] = []
    for photo in photos:
        tensor = None
        features = None
        try:
            with Image.open(photo.path) as image:
                tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(device)
            with torch.inference_mode():
                features = model.encode_image(tensor)
                features = F.normalize(features, dim=-1)
            photo.embedding = features.squeeze(0).detach().float().cpu()
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            failed.append(f"{photo.label}: {exc}")
        finally:
            if tensor is not None:
                del tensor
            if features is not None:
                del features
    return failed


def rank_destination(
    query: torch.Tensor,
    photos: list[Photograph],
    destination: str,
    excluded: set[int],
) -> dict[str, object] | None:
    grouped: dict[str, list[float]] = defaultdict(list)
    for index, photo in enumerate(photos):
        if index in excluded or photo.destination_slug != destination or photo.embedding is None:
            continue
        grouped[photo.checkpoint_id].append(cosine(query, photo.embedding))
    if not grouped:
        return None
    ranked = sorted(
        (
            (checkpoint_id, max(scores), len(scores))
            for checkpoint_id, scores in grouped.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    best_id, best_score, best_count = ranked[0]
    if len(ranked) == 1:
        second_id, second_score, margin = "", "", None
    else:
        second_id, second_score, _second_count = ranked[1]
        margin = best_score - second_score
    score_ok = best_score >= MIN_SIMILARITY
    margin_ok = margin is None or margin >= MIN_MARGIN
    accepted = score_ok and margin_ok
    reject_reason = ""
    if not accepted:
        reject_reason = "margin" if score_ok else "similarity"
    return {
        "best_checkpoint_id": best_id,
        "best_similarity": best_score,
        "best_reference_count": best_count,
        "second_checkpoint_id": second_id,
        "second_similarity": second_score,
        "margin": margin,
        "accepted": accepted,
        "accepted_checkpoint_id": best_id if accepted else "",
        "reject_reason": reject_reason,
        "checkpoint_count": len(ranked),
    }


def blank_rank() -> dict[str, object]:
    return {
        "best_checkpoint_id": "",
        "best_similarity": "",
        "best_reference_count": "",
        "second_checkpoint_id": "",
        "second_similarity": "",
        "margin": "",
        "accepted": False,
        "accepted_checkpoint_id": "",
        "reject_reason": "no_remaining_references",
        "checkpoint_count": 0,
    }


def outcome_for(photo: Photograph, decision: dict[str, object], sibling_count: int) -> str:
    if sibling_count == 0:
        if decision["accepted"]:
            return "false_match_without_sibling"
        return "not_evaluable_no_sibling"
    if decision["accepted"] and decision["accepted_checkpoint_id"] == photo.checkpoint_id:
        return "accepted_correct"
    if decision["accepted"]:
        return "false_match"
    if decision["best_checkpoint_id"] == photo.checkpoint_id:
        return "rejected_genuine_ranked_first"
    return "rejected_genuine_ranked_lower"


def fmt(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.8f}"
    return str(value)


def main() -> int:
    started = time.perf_counter()
    photos, exclusion_notes = load_photos()
    device = select_device()
    model, preprocess = load_model(device)
    embed_started = time.perf_counter()
    failed = embed(model, preprocess, device, photos)
    embed_seconds = time.perf_counter() - embed_started
    valid = [photo for photo in photos if photo.embedding is not None]
    if not valid:
        print("No photographs could be embedded.")
        return 1

    by_hash: dict[str, list[Photograph]] = defaultdict(list)
    for photo in valid:
        by_hash[photo.sha256].append(photo)
    exact_duplicates = [group for group in by_hash.values() if len(group) > 1]

    same_checkpoint_pairs: list[tuple[float, Photograph, Photograph]] = []
    different_pairs: list[tuple[float, Photograph, Photograph]] = []
    for left_index, left in enumerate(valid):
        for right in valid[left_index + 1 :]:
            score = cosine(left.embedding, right.embedding)
            if left.key == right.key:
                same_checkpoint_pairs.append((score, left, right))
            else:
                different_pairs.append((score, left, right))
    same_checkpoint_pairs.sort(key=lambda item: item[0], reverse=True)
    different_pairs.sort(key=lambda item: item[0], reverse=True)
    near_pairs = [item for item in same_checkpoint_pairs if item[0] >= NEAR_DUPLICATE]
    different_at_or_above_floor = [item for item in different_pairs if item[0] >= MIN_SIMILARITY]

    self_scores = [cosine(photo.embedding, photo.embedding) for photo in valid]
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for photo in valid:
        counts[photo.key] += 1

    rows: list[dict[str, str]] = []
    same_outcomes: list[tuple[Photograph, str, dict[str, object]]] = []
    independent_outcomes: list[tuple[Photograph, str, dict[str, object]]] = []
    cross_rows: list[dict[str, str]] = []

    destinations = sorted({photo.destination_slug for photo in valid})
    for index, photo in enumerate(valid):
        siblings = counts[photo.key] - 1
        raw = rank_destination(photo.embedding, valid, photo.destination_slug, {index}) or blank_rank()
        raw_outcome = outcome_for(photo, raw, siblings)
        near_support = bool(raw["accepted"]) and isinstance(raw["best_similarity"], float) and raw["best_similarity"] >= NEAR_DUPLICATE
        if near_support and raw_outcome == "accepted_correct":
            raw_outcome = "accepted_correct_near_duplicate"
        same_outcomes.append((photo, raw_outcome, raw))

        excluded = {index}
        for other_index, other in enumerate(valid):
            if other_index != index and other.key == photo.key and cosine(photo.embedding, other.embedding) >= NEAR_DUPLICATE:
                excluded.add(other_index)
        independent_siblings = sum(
            1
            for other_index, other in enumerate(valid)
            if other_index not in excluded and other.key == photo.key
        )
        independent = rank_destination(photo.embedding, valid, photo.destination_slug, excluded) or blank_rank()
        independent_outcome = outcome_for(photo, independent, independent_siblings)
        independent_outcomes.append((photo, independent_outcome, independent))

        rows.append(
            {
                "record_type": "same_destination_leave_one_out",
                "query_destination": photo.destination_slug,
                "query_checkpoint": photo.checkpoint_id,
                "query_file": photo.path.name,
                "collection": photo.collection,
                "remaining_same_checkpoint_photos": str(siblings),
                "best_checkpoint_id": str(raw["best_checkpoint_id"]),
                "best_similarity": fmt(raw["best_similarity"]),
                "second_checkpoint_id": str(raw["second_checkpoint_id"]),
                "second_similarity": fmt(raw["second_similarity"]),
                "margin": fmt(raw["margin"]),
                "margin_available": "yes" if raw["margin"] is not None else "no",
                "rule_decision": "match" if raw["accepted"] else "no_match",
                "accepted_checkpoint_id": str(raw["accepted_checkpoint_id"]),
                "reject_reason": str(raw["reject_reason"]),
                "outcome": raw_outcome,
                "independent_outcome": independent_outcome,
                "independent_best_similarity": fmt(independent["best_similarity"]),
                "independent_margin": fmt(independent["margin"]),
                "note": photo.viewpoint,
            }
        )

        for destination in destinations:
            if destination == photo.destination_slug:
                continue
            decision = rank_destination(photo.embedding, valid, destination, set()) or blank_rank()
            cross_outcome = "cross_destination_false_match" if decision["accepted"] else "cross_destination_rejection"
            cross = {
                "record_type": "cross_destination",
                "query_destination": photo.destination_slug,
                "query_checkpoint": photo.checkpoint_id,
                "query_file": photo.path.name,
                "collection": photo.collection,
                "remaining_same_checkpoint_photos": "",
                "best_checkpoint_id": str(decision["best_checkpoint_id"]),
                "best_similarity": fmt(decision["best_similarity"]),
                "second_checkpoint_id": str(decision["second_checkpoint_id"]),
                "second_similarity": fmt(decision["second_similarity"]),
                "margin": fmt(decision["margin"]),
                "margin_available": "yes" if decision["margin"] is not None else "no",
                "rule_decision": "match" if decision["accepted"] else "no_match",
                "accepted_checkpoint_id": str(decision["accepted_checkpoint_id"]),
                "reject_reason": str(decision["reject_reason"]),
                "outcome": cross_outcome,
                "independent_outcome": "",
                "independent_best_similarity": "",
                "independent_margin": "",
                "note": f"Compared only with {destination}. This is not a same-checkpoint recognition test.",
            }
            rows.append(cross)
            cross_rows.append(cross)

    fieldnames = list(rows[0].keys())
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def tally(items: list[tuple[Photograph, str, dict[str, object]]]) -> dict[str, int]:
        counts_by_name: dict[str, int] = defaultdict(int)
        for _photo, name, _decision in items:
            counts_by_name[name] += 1
        return counts_by_name

    raw_tally = tally(same_outcomes)
    independent_tally = tally(independent_outcomes)
    cross_false = sum(1 for row in cross_rows if row["outcome"] == "cross_destination_false_match")
    cross_reject = sum(1 for row in cross_rows if row["outcome"] == "cross_destination_rejection")
    margin_unavailable = sum(1 for _photo, _name, decision in same_outcomes if decision["margin"] is None)

    lines = [
        "Acceptance-rule audit of stored reference photographs",
        f"Rules audited, not changed: minimum cosine similarity {MIN_SIMILARITY}, minimum margin {MIN_MARGIN}.",
        "Aggregation: highest cosine similarity among the remaining photographs of each checkpoint.",
        "The query photograph is removed before scoring. A same-image score is not a recognition result.",
        f"Device: {device}" + (f" ({torch.cuda.get_device_name(device)})" if device.type == "cuda" else ""),
        f"Photographs embedded: {len(valid)}",
        f"Embedding time: {embed_seconds:.2f} s",
        f"Total time: {time.perf_counter() - started:.2f} s",
        f"Same-image cosine similarity: {min(self_scores):.6f} to {max(self_scores):.6f}. Excluded from every decision below.",
        "",
        "What the earlier evaluation files establish",
        "embedding_evaluation.csv compares the original 22 reference photographs with each other.",
        "expanded_leave_one_out.csv compares the 42 stored photographs and asks whether another stored photograph of the same checkpoint ranks first.",
        "Those files do not contain visitor photographs, and they do not apply the 0.97 and 0.05 service rules.",
        "A rank of 1 is not an accepted recognition under the service rules.",
        "",
        "Leakage checks",
        f"Exact file-hash groups with more than one photograph: {len(exact_duplicates)}.",
    ]
    for group in exact_duplicates:
        lines.append("  identical bytes: " + " | ".join(photo.label for photo in group))
    if not exact_duplicates:
        lines.append("  No two evaluated files have the same SHA-256 digest.")
    lines.append(f"Same-checkpoint pairs at or above the {NEAR_DUPLICATE} duplicate screen: {len(near_pairs)}.")
    for score, left, right in near_pairs:
        lines.append(f"  {score:.4f}  {left.label}  vs  {right.label}")
    if not near_pairs:
        lines.append("  None.")
    close_same = [item for item in same_checkpoint_pairs if MIN_SIMILARITY <= item[0] < NEAR_DUPLICATE]
    lines.append(
        f"Other same-checkpoint pairs from {MIN_SIMILARITY} up to but not including {NEAR_DUPLICATE}: {len(close_same)}."
    )
    for score, left, right in close_same:
        lines.append(f"  {score:.4f}  {left.label}  vs  {right.label}")
    if not close_same:
        lines.append("  None.")
    lines.append(
        f"Different-checkpoint pairs at or above {MIN_SIMILARITY}: {len(different_at_or_above_floor)}."
    )
    lines.append("Highest different-checkpoint pairs:")
    for score, left, right in different_pairs[:8]:
        same_destination = "same destination" if left.destination_slug == right.destination_slug else "different destinations"
        lines.append(f"  {score:.4f}  {left.label}  vs  {right.label}  ({same_destination})")
    lines.extend(["", "Excluded rows"])
    lines.extend(exclusion_notes[:25])
    if len(exclusion_notes) > 25:
        lines.append(f"  {len(exclusion_notes) - 25} further shortlist or missing-file rows were excluded.")
    if failed:
        lines.extend(failed)

    lines.extend(["", "Photographs by checkpoint"])
    for key in sorted(counts):
        lines.append(f"  {key[0]}/{key[1]}: {counts[key]}")

    lines.extend(
        [
            "",
            "Same-destination leave-one-out under the service rules",
            "A query counts as recognition evidence only when another photograph of the same checkpoint remains.",
            "Removing the query from a one-photograph checkpoint cannot measure recognition of that checkpoint.",
            f"Queries: {len(same_outcomes)}.",
            f"Margin unavailable because the destination had only one remaining photographed checkpoint: {margin_unavailable}.",
        ]
    )
    for name in (
        "accepted_correct",
        "accepted_correct_near_duplicate",
        "false_match",
        "false_match_without_sibling",
        "rejected_genuine_ranked_first",
        "rejected_genuine_ranked_lower",
        "not_evaluable_no_sibling",
    ):
        lines.append(f"  {name}: {raw_tally[name]}")

    lines.append("Failure and acceptance rows:")
    for photo, name, decision in same_outcomes:
        if name == "not_evaluable_no_sibling":
            continue
        margin = decision["margin"]
        margin_text = "margin unavailable" if margin is None else f"margin {margin:.4f}"
        lines.append(
            f"  {name}: {photo.label} best {decision['best_checkpoint_id']} "
            f"{decision['best_similarity']:.4f} vs {decision['second_checkpoint_id'] or 'none'} "
            f"{margin_text}"
        )

    lines.extend(
        [
            "",
            "Same test after also removing same-checkpoint photographs at or above the duplicate screen",
        ]
    )
    for name in (
        "accepted_correct",
        "false_match",
        "false_match_without_sibling",
        "rejected_genuine_ranked_first",
        "rejected_genuine_ranked_lower",
        "not_evaluable_no_sibling",
    ):
        lines.append(f"  {name}: {independent_tally[name]}")
    lines.append("Rows whose outcome changes once near-duplicate support is removed:")
    for (photo, raw_name, _raw), (_photo, independent_name, independent) in zip(same_outcomes, independent_outcomes):
        if raw_name == independent_name:
            continue
        lines.append(
            f"  {photo.label}: {raw_name} -> {independent_name} "
            f"(remaining best {independent['best_checkpoint_id']} {fmt(independent['best_similarity'])})"
        )

    lines.extend(
        [
            "",
            "Cross-destination trials",
            "Each photograph is compared with every other destination's full reference set.",
            "The photograph is not a reference for those destinations. Rejection here is not evidence that its own checkpoint would be recognized.",
            f"Trials: {len(cross_rows)}. False matches: {cross_false}. Rejections: {cross_reject}.",
        ]
    )
    if cross_false:
        for row in cross_rows:
            if row["outcome"] == "cross_destination_false_match":
                lines.append(
                    f"  false match: {row['query_destination']}/{row['query_checkpoint']}/{row['query_file']} "
                    f"accepted as {row['accepted_checkpoint_id']} at similarity {row['best_similarity']}"
                )
    else:
        highest_cross = max(
            (float(row["best_similarity"]) for row in cross_rows if row["best_similarity"]),
            default=0.0,
        )
        lines.append(f"Highest score in a cross-destination trial: {highest_cross:.4f}.")

    lines.extend(
        [
            "",
            "Threshold conclusion",
            "These photographs are the reference collection, not a separate visitor-photo test set.",
            "Fitting a new similarity or margin to these scores would reuse the same images the service stores.",
            "The audit therefore does not justify changing either production threshold.",
            "",
            "Independent test photographs still needed",
            "Collect new photographs that are not files already in reference_manifest.csv.",
            "For each important checkpoint, use several camera positions: front, side, closer detail, and a farther view.",
            "Include the checkpoints that still have one photograph or none, because this audit cannot measure them.",
            "Include difficult negatives: other checkpoints at the same destination, especially halls and gates that already score near one another.",
            "Keep those new files out of the reference gallery until the rules are reviewed.",
            "Do not treat another crop or export of a stored reference file as a new viewpoint.",
            "",
            f"Rows: {RESULTS_PATH}",
            "Existing evaluation CSV files were not modified.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
