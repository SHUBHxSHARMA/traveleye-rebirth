"""Red Fort leave-one-image-out experiment.

Reads the existing Red Fort photographs and the cached OpenCLIP ViT-B-32
weights. It does not download files, train a model, change production
thresholds, or write into the live reference gallery or the earlier
evaluation artifacts.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PIL import Image, ImageFilter, UnidentifiedImageError

from recognition import (
    DEFAULT_MIN_MARGIN,
    DEFAULT_MIN_SIMILARITY,
    DESTINATIONS,
    WEIGHTS,
)

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "reference_manifest.csv"
REPORT_PATH = SCRIPT_DIR / "red_fort_recognition_experiment.md"
INVENTORY_PATH = SCRIPT_DIR / "red_fort_experiment_inventory.csv"
TRIALS_PATH = SCRIPT_DIR / "red_fort_experiment_trials.csv"
SUMMARY_PATH = SCRIPT_DIR / "red_fort_experiment_summary.csv"
PAIRS_PATH = SCRIPT_DIR / "red_fort_experiment_pairs.csv"
CAPTURE_TEMPLATE_PATH = SCRIPT_DIR / "red_fort_independent_capture_template.csv"

PROTECTED = {
    "acceptance_audit.csv",
    "acceptance_audit_report.txt",
    "embedding_evaluation.csv",
    "embedding_evaluation_expanded.csv",
    "expanded_leave_one_out.csv",
    "expanded_leave_one_out_summary.txt",
    "reference_manifest.csv",
    "reference_coverage_inventory.csv",
    "reference_coverage_plan.md",
}

# Leakage screen shared with the earlier audit. It is not an acceptance rule.
NEAR_DUPLICATE = 0.98
DESTINATION = "red-fort"
CHECKPOINT_ORDER = list(DESTINATIONS[DESTINATION])
CHECKPOINT_NAMES = DESTINATIONS[DESTINATION]

# Fixed before any score was inspected. Do not edit these to chase the 16 photographs.
TEXT_PROMPT = "a photograph of {name} at the Red Fort in Delhi"
UNSHARP_RADIUS = 1.5
UNSHARP_PERCENT = 120
UNSHARP_THRESHOLD = 2
CROP_FRACTIONS = (0.8, 0.6)

IMAGE_STRATEGIES = (
    ("baseline_max", "baseline", "max"),
    ("baseline_mean", "baseline", "mean"),
    ("multicrop_max", "multicrop", "max"),
    ("center60_max", "center60", "max"),
    ("unsharp_max", "unsharp", "max"),
)


@dataclass
class Photograph:
    collection: str
    checkpoint_id: str
    path: Path
    sha256: str
    width: int
    height: int
    byte_size: int
    embeddings: dict[str, object] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return CHECKPOINT_NAMES[self.checkpoint_id]

    @property
    def label(self) -> str:
        return f"{self.checkpoint_id}/{self.path.name}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cosine(left, right) -> float:
    import torch

    return float(torch.dot(left, right).item())


def center_crop(image: Image.Image, fraction: float) -> Image.Image:
    width, height = image.size
    crop_width = max(1, int(round(width * fraction)))
    crop_height = max(1, int(round(height * fraction)))
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    return image.crop((left, top, left + crop_width, top + crop_height))


def load_manifest() -> tuple[list[Photograph], list[dict[str, str]], list[str], list[Path]]:
    photos: list[Photograph] = []
    shortlist: list[dict[str, str]] = []
    notes: list[str] = []
    manifest_paths: set[Path] = set()
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["local_path"]:
            manifest_paths.add(Path(row["local_path"]).resolve())
        if row["destination_slug"] != DESTINATION:
            continue
        if row["collection"] == "shortlist":
            shortlist.append(row)
            continue
        if row["collection"] not in {"existing", "added"}:
            notes.append(f"Skipped collection {row['collection']} for {row['checkpoint_id']}.")
            continue
        if row["checkpoint_id"] not in CHECKPOINT_NAMES:
            notes.append(f"Skipped unknown checkpoint {row['checkpoint_id']}.")
            continue
        path = Path(row["local_path"])
        if not path.is_file():
            notes.append(f"Missing file for {row['checkpoint_id']}: {path}")
            continue
        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
        except (OSError, UnidentifiedImageError) as exc:
            notes.append(f"Unreadable file {path.name}: {exc}")
            continue
        photos.append(
            Photograph(
                collection=row["collection"],
                checkpoint_id=row["checkpoint_id"],
                path=path,
                sha256=file_sha256(path),
                width=width,
                height=height,
                byte_size=path.stat().st_size,
            )
        )
    photos.sort(key=lambda photo: (CHECKPOINT_ORDER.index(photo.checkpoint_id), photo.path.name.lower()))
    extras: list[Path] = []
    public_dirs = {photo.path.parent.resolve() for photo in photos}
    for directory in public_dirs:
        for candidate in sorted(directory.glob("*.jpg")):
            if candidate.resolve() not in manifest_paths:
                extras.append(candidate)
    return photos, shortlist, notes, extras


def select_device():
    import torch

    if not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        torch.zeros(1, device="cuda")
    except Exception:
        return torch.device("cpu")
    return torch.device("cuda")


def load_model(device):
    import open_clip
    from open_clip.constants import OPENAI_DATASET_MEAN, OPENAI_DATASET_STD

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
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    return model, preprocess, tokenizer


def embed_pil(model, preprocess, device, image: Image.Image):
    import torch
    import torch.nn.functional as F

    tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(device)
    try:
        with torch.inference_mode():
            features = model.encode_image(tensor)
            features = F.normalize(features, dim=-1)
            return features.squeeze(0).detach().float().cpu()
    finally:
        del tensor


def embed_average(model, preprocess, device, images: list[Image.Image]):
    import torch
    import torch.nn.functional as F

    vectors = [embed_pil(model, preprocess, device, image) for image in images]
    mean = torch.stack(vectors, dim=0).mean(dim=0)
    return F.normalize(mean, dim=0)


def embed_photos(model, preprocess, device, photos: list[Photograph]) -> None:
    for photo in photos:
        with Image.open(photo.path) as image:
            image.load()
            rgb = image.convert("RGB")
            photo.embeddings["baseline"] = embed_pil(model, preprocess, device, rgb)
            crops = [rgb, center_crop(rgb, CROP_FRACTIONS[0]), center_crop(rgb, CROP_FRACTIONS[1])]
            photo.embeddings["multicrop"] = embed_average(model, preprocess, device, crops)
            photo.embeddings["center60"] = embed_pil(model, preprocess, device, center_crop(rgb, 0.6))
            sharpened = rgb.filter(
                ImageFilter.UnsharpMask(
                    radius=UNSHARP_RADIUS,
                    percent=UNSHARP_PERCENT,
                    threshold=UNSHARP_THRESHOLD,
                )
            )
            photo.embeddings["unsharp"] = embed_pil(model, preprocess, device, sharpened)


def embed_prompts(model, tokenizer, device) -> dict[str, object]:
    import torch
    import torch.nn.functional as F

    prompts = [TEXT_PROMPT.format(name=CHECKPOINT_NAMES[checkpoint_id]) for checkpoint_id in CHECKPOINT_ORDER]
    tokens = tokenizer(prompts).to(device)
    try:
        with torch.inference_mode():
            features = model.encode_text(tokens)
            features = F.normalize(features, dim=-1).detach().float().cpu()
    finally:
        del tokens
    return {checkpoint_id: features[index] for index, checkpoint_id in enumerate(CHECKPOINT_ORDER)}


def rank_checkpoints(
    query,
    photos: list[Photograph],
    skip: set[int],
    embedding_key: str,
    aggregate: str,
) -> list[tuple[str, float, int]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for index, photo in enumerate(photos):
        if index in skip:
            continue
        grouped[photo.checkpoint_id].append(cosine(query, photo.embeddings[embedding_key]))
    scored: list[tuple[str, float, int]] = []
    for checkpoint_id, values in grouped.items():
        if aggregate == "max":
            score = max(values)
        elif aggregate == "mean":
            score = sum(values) / len(values)
        else:
            raise ValueError(aggregate)
        scored.append((checkpoint_id, score, len(values)))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored


def acceptance(scored: list[tuple[str, float, int]]) -> tuple[bool, str, float | None]:
    if not scored:
        return False, "", None
    best_id, best_score, _count = scored[0]
    margin = None if len(scored) == 1 else best_score - scored[1][1]
    score_ok = best_score >= DEFAULT_MIN_SIMILARITY
    margin_ok = margin is None or margin >= DEFAULT_MIN_MARGIN
    if score_ok and margin_ok:
        return True, best_id, margin
    return False, "", margin


def outcome(evaluable: bool, true_id: str, top1: str, accepted: bool, accepted_id: str) -> str:
    if not evaluable:
        if accepted and accepted_id != true_id:
            return "not_evaluable_false_accept"
        return "not_evaluable_rejected"
    if accepted and accepted_id == true_id:
        return "ranked_correct_accepted"
    if accepted and accepted_id != true_id:
        return "ranked_wrong_accepted"
    if top1 == true_id:
        return "ranked_correct_rejected"
    return "ranked_wrong_rejected"


def skip_indices(photos: list[Photograph], query_index: int, drop_near_duplicates: bool) -> set[int]:
    skip = {query_index}
    if not drop_near_duplicates:
        return skip
    query = photos[query_index]
    for index, photo in enumerate(photos):
        if index == query_index or photo.checkpoint_id != query.checkpoint_id:
            continue
        if cosine(query.embeddings["baseline"], photo.embeddings["baseline"]) >= NEAR_DUPLICATE:
            skip.add(index)
    return skip


def build_image_trials(photos: list[Photograph]) -> list[dict[str, object]]:
    counts: dict[str, int] = defaultdict(int)
    for photo in photos:
        counts[photo.checkpoint_id] += 1
    trials: list[dict[str, object]] = []
    for exclusion_name, drop_near in (
        ("held_out_self", False),
        ("held_out_self_and_near_duplicates", True),
    ):
        for strategy, embedding_key, aggregate in IMAGE_STRATEGIES:
            for index, photo in enumerate(photos):
                skip = skip_indices(photos, index, drop_near)
                if index not in skip:
                    raise RuntimeError(f"Query was not removed: {photo.label}")
                remaining_true = sum(
                    1
                    for other_index, other in enumerate(photos)
                    if other_index not in skip and other.checkpoint_id == photo.checkpoint_id
                )
                evaluable = remaining_true > 0
                scored = rank_checkpoints(photo.embeddings[embedding_key], photos, skip, embedding_key, aggregate)
                if any(other_index in skip for other_index in range(len(photos)) if other_index == index) is False:
                    raise RuntimeError("Self-match guard failed.")
                top1 = scored[0][0] if scored else ""
                best = scored[0][1] if scored else ""
                second_id = scored[1][0] if len(scored) > 1 else ""
                second = scored[1][1] if len(scored) > 1 else ""
                accepted, accepted_id, margin = acceptance(scored)
                true_score = ""
                rival_score = ""
                for checkpoint_id, score, _count in scored:
                    if checkpoint_id == photo.checkpoint_id:
                        true_score = score
                    elif rival_score == "":
                        rival_score = score
                trials.append(
                    {
                        "strategy": strategy,
                        "exclusion": exclusion_name,
                        "rule": "production_0.97_0.05",
                        "query_checkpoint_id": photo.checkpoint_id,
                        "query_file": photo.path.name,
                        "checkpoint_photo_count": counts[photo.checkpoint_id],
                        "evaluable": evaluable,
                        "top1_checkpoint_id": top1,
                        "top1_correct": bool(evaluable and top1 == photo.checkpoint_id),
                        "best_similarity": best,
                        "second_checkpoint_id": second_id,
                        "second_similarity": second,
                        "true_checkpoint_similarity": true_score,
                        "margin": "" if margin is None else margin,
                        "accepted": accepted,
                        "accepted_checkpoint_id": accepted_id,
                        "outcome": outcome(evaluable, photo.checkpoint_id, top1, accepted, accepted_id),
                        "tied_top": bool(len(scored) > 1 and abs(scored[0][1] - scored[1][1]) < 1e-6),
                    }
                )
    return trials


def build_text_trials(photos: list[Photograph], text_vectors: dict[str, object]) -> list[dict[str, object]]:
    counts: dict[str, int] = defaultdict(int)
    for photo in photos:
        counts[photo.checkpoint_id] += 1
    sibling_ids = {checkpoint_id for checkpoint_id, count in counts.items() if count > 1}
    trials: list[dict[str, object]] = []
    for photo in photos:
        scored = []
        for checkpoint_id in CHECKPOINT_ORDER:
            scored.append((checkpoint_id, cosine(photo.embeddings["baseline"], text_vectors[checkpoint_id]), 0))
        scored.sort(key=lambda item: (-item[1], item[0]))
        top1, best, _unused = scored[0]
        second_id, second, _unused = scored[1]
        margin = best - second
        correct = top1 == photo.checkpoint_id
        trials.append(
            {
                "strategy": "text_zeroshot",
                "exclusion": "no_gallery",
                "rule": "top1_only",
                "query_checkpoint_id": photo.checkpoint_id,
                "query_file": photo.path.name,
                "checkpoint_photo_count": counts[photo.checkpoint_id],
                "evaluable": photo.checkpoint_id in sibling_ids,
                "top1_checkpoint_id": top1,
                "top1_correct": correct,
                "best_similarity": best,
                "second_checkpoint_id": second_id,
                "second_similarity": second,
                "true_checkpoint_similarity": next(score for checkpoint_id, score, _count in scored if checkpoint_id == photo.checkpoint_id),
                "margin": margin,
                "accepted": "",
                "accepted_checkpoint_id": "",
                "outcome": "text_top1_correct" if correct else "text_top1_wrong",
                "tied_top": abs(best - second) < 1e-6,
                "population": "sibling_checkpoint" if photo.checkpoint_id in sibling_ids else "single_photo_checkpoint",
            }
        )
    return trials


def pair_rows(photos: list[Photograph]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for left_index, left in enumerate(photos):
        for right in photos[left_index + 1 :]:
            score = cosine(left.embeddings["baseline"], right.embeddings["baseline"])
            same = left.checkpoint_id == right.checkpoint_id
            rows.append(
                {
                    "left_checkpoint_id": left.checkpoint_id,
                    "left_file": left.path.name,
                    "right_checkpoint_id": right.checkpoint_id,
                    "right_file": right.path.name,
                    "same_checkpoint": same,
                    "cosine": score,
                    "exact_sha256": left.sha256 == right.sha256,
                    "near_duplicate_screen": same and score >= NEAR_DUPLICATE,
                }
            )
    rows.sort(key=lambda row: -float(row["cosine"]))
    return rows


def summary_rows(trials: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for trial in trials:
        if trial["strategy"] == "text_zeroshot":
            continue
        grouped[(str(trial["strategy"]), str(trial["exclusion"]))].append(trial)
    rows: list[dict[str, object]] = []
    for (strategy, exclusion), group in grouped.items():
        evaluable = [trial for trial in group if trial["evaluable"]]
        false_all = [trial for trial in group if trial["outcome"] in {"ranked_wrong_accepted", "not_evaluable_false_accept"}]
        false_evaluable = [trial for trial in evaluable if trial["outcome"] == "ranked_wrong_accepted"]
        accepted_correct = [trial for trial in evaluable if trial["outcome"] == "ranked_correct_accepted"]
        top1 = [trial for trial in evaluable if trial["top1_correct"]]
        rejected = [trial for trial in evaluable if not trial["accepted"]]
        rows.append(
            {
                "strategy": strategy,
                "exclusion": exclusion,
                "rule": "production_0.97_0.05",
                "all_queries": len(group),
                "evaluable_queries": len(evaluable),
                "not_evaluable_queries": len(group) - len(evaluable),
                "top1_correct": len(top1),
                "top1_accuracy": ratio(len(top1), len(evaluable)),
                "accepted_correct": len(accepted_correct),
                "accepted_match_rate": ratio(len(accepted_correct), len(evaluable)),
                "false_accept_evaluable": len(false_evaluable),
                "false_accept_rate_evaluable": ratio(len(false_evaluable), len(evaluable)),
                "rejected_evaluable": len(rejected),
                "rejection_rate_evaluable": ratio(len(rejected), len(evaluable)),
                "false_accept_all": len(false_all),
                "false_accept_rate_all": ratio(len(false_all), len(group)),
                "ties": sum(1 for trial in group if trial["tied_top"]),
            }
        )
    text = [trial for trial in trials if trial["strategy"] == "text_zeroshot"]
    for population, group in (
        ("all_red_fort_photos", text),
        ("sibling_checkpoints_only", [trial for trial in text if trial["evaluable"]]),
    ):
        correct = sum(1 for trial in group if trial["top1_correct"])
        rows.append(
            {
                "strategy": "text_zeroshot",
                "exclusion": population,
                "rule": "top1_only",
                "all_queries": len(group),
                "evaluable_queries": len(group),
                "not_evaluable_queries": 0,
                "top1_correct": correct,
                "top1_accuracy": ratio(correct, len(group)),
                "accepted_correct": "",
                "accepted_match_rate": "",
                "false_accept_evaluable": "",
                "false_accept_rate_evaluable": "",
                "rejected_evaluable": "",
                "rejection_rate_evaluable": "",
                "false_accept_all": "",
                "false_accept_rate_all": "",
                "ties": sum(1 for trial in group if trial["tied_top"]),
            }
        )
    return rows


def ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    return f"{numerator / denominator:.4f}"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if path.name in PROTECTED:
        raise RuntimeError(f"Refusing to overwrite {path.name}")
    if not rows:
        raise RuntimeError(f"No rows for {path.name}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_cell(row.get(key, "")) for key in fieldnames})


def format_cell(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.8f}"
    return str(value)


def count_line(summary: dict[str, object], label: str) -> str:
    correct = summary[label]
    if label == "top1_correct":
        total = summary["evaluable_queries"]
    elif label == "accepted_correct":
        total = summary["evaluable_queries"]
    elif label == "false_accept_evaluable":
        total = summary["evaluable_queries"]
    elif label == "rejected_evaluable":
        total = summary["evaluable_queries"]
    elif label == "false_accept_all":
        total = summary["all_queries"]
    else:
        total = ""
    return f"{correct}/{total}"


def find_summary(rows: list[dict[str, object]], strategy: str, exclusion: str) -> dict[str, object]:
    for row in rows:
        if row["strategy"] == strategy and row["exclusion"] == exclusion:
            return row
    raise KeyError((strategy, exclusion))


def sim(value: object) -> str:
    if value == "" or value is None:
        return ""
    return f"{float(value):.4f}"


def write_report(
    photos: list[Photograph],
    shortlist: list[dict[str, str]],
    notes: list[str],
    extras: list[Path],
    pairs: list[dict[str, object]],
    trials: list[dict[str, object]],
    summaries: list[dict[str, object]],
        device_name: str,
        embed_seconds: float,
        text_seconds: float,
        self_min: float,
        self_max: float,
    ) -> None:
    counts: dict[str, int] = defaultdict(int)
    for photo in photos:
        counts[photo.checkpoint_id] += 1
    exact = [row for row in pairs if row["exact_sha256"]]
    near = [row for row in pairs if row["near_duplicate_screen"]]
    same_pairs = [row for row in pairs if row["same_checkpoint"]]
    cross_pairs = [row for row in pairs if not row["same_checkpoint"]]
    baseline = [
        trial
        for trial in trials
        if trial["strategy"] == "baseline_max" and trial["exclusion"] == "held_out_self"
    ]
    base_summary = find_summary(summaries, "baseline_max", "held_out_self")
    near_summary = find_summary(summaries, "baseline_max", "held_out_self_and_near_duplicates")
    text_all = find_summary(summaries, "text_zeroshot", "all_red_fort_photos")
    text_sibling = find_summary(summaries, "text_zeroshot", "sibling_checkpoints_only")
    lines: list[str] = []
    add = lines.append
    add("# Red Fort recognition experiment")
    add("")
    add(f"Run date: {date.today().isoformat()}.")
    add("")
    add("This run reads the Red Fort photographs already on disk and the cached OpenCLIP ViT-B-32 weights. It does not change the scanner, the frontend, the API, the production thresholds, or the live gallery. It does not download photographs or weights, and it does not train a model.")
    add("")
    add("## What was tested")
    add("")
    add(f"Model: OpenCLIP ViT-B-32, QuickGELU enabled, OpenAI image mean and standard deviation, bicubic resize on the shortest side. Weights: `{WEIGHTS}`. Device: {device_name}. The four image representations took {embed_seconds:.1f} seconds. The ten text prompts took {text_seconds:.1f} seconds.")
    add("")
    add("The image strategies use one shared leave-one-image-out procedure inside `red-fort` only. The query photograph is removed before scoring. A checkpoint score is either the maximum cosine among that checkpoint's remaining photographs, which is the production aggregation, or the mean of those cosines. A result is accepted only when the best score is at least 0.97 and the margin to the next checkpoint is at least 0.05. Those two numbers are imported from `recognition.py`. They were not changed, and no other cutoff was selected.")
    add("")
    add("The representations, fixed before looking at these scores, are:")
    add("")
    add("- `baseline_max` and `baseline_mean`: the production full-frame preprocess.")
    add("- `multicrop_max`: the mean of three normalized embeddings, from the full frame, a centered 80 percent crop, and a centered 60 percent crop, then normalized again.")
    add("- `center60_max`: the centered 60 percent crop only.")
    add(f"- `unsharp_max`: an unsharp mask (radius {UNSHARP_RADIUS}, percent {UNSHARP_PERCENT}, threshold {UNSHARP_THRESHOLD}) and then the production preprocess.")
    add(f"- `text_zeroshot`: the same model's text tower. Each checkpoint has one prompt, `{TEXT_PROMPT}`. The display names are the names already in `recognition.DESTINATIONS`. Image-text cosine is not judged with the 0.97 rule, because that rule was set for image-image retrieval and these scores sit on a different scale.")
    add("")
    add("A query is evaluable for image retrieval when at least one other photograph of its true checkpoint remains. Top-1 accuracy, accepted-match rate, and rejection rate use that evaluable set as the denominator. False-accept rate is also reported over every Red Fort photograph, because a single-photo checkpoint can still be given the wrong name. Correct ranking means the true checkpoint has the highest score. Accepted recognition means the production rule also accepts that checkpoint. Those are different outcomes.")
    add("")
    add(f"Self-similarity of each baseline embedding against itself was {self_min:.6f} to {self_max:.6f}. Those values are a normalization check. They are not recognition trials.")
    add("")
    add("## Inventory")
    add("")
    add(f"Manifest rows for Red Fort with a local file: {len(photos)}. Shortlist rows with no local file, excluded from scoring: {len(shortlist)}. Exact SHA-256 duplicates: {len(exact)}.")
    add("")
    add("| Checkpoint | Photographs on disk | Shortlisted, not on disk | Evaluable for retrieval |")
    add("| --- | ---: | ---: | --- |")
    short_counts: dict[str, int] = defaultdict(int)
    for row in shortlist:
        short_counts[row["checkpoint_id"]] += 1
    for checkpoint_id in CHECKPOINT_ORDER:
        evaluable = "yes" if counts[checkpoint_id] > 1 else "no, the only photograph would be the query"
        add(
            f"| {CHECKPOINT_NAMES[checkpoint_id]} | {counts[checkpoint_id]} | {short_counts[checkpoint_id]} | {evaluable} |"
        )
    add("")
    if notes:
        add("Load notes:")
        add("")
        for note in notes:
            add(f"- {note}")
        add("")
    if extras:
        add("JPEG files in the same folder as these references that are not listed in the manifest were not embedded:")
        add("")
        for extra in extras:
            add(f"- `{extra.name}`")
        add("")
    add("Same-checkpoint baseline pairs:")
    add("")
    add("| Checkpoint | Files | Cosine | Near-duplicate screen (0.98) |")
    add("| --- | --- | ---: | --- |")
    for row in sorted(same_pairs, key=lambda item: (str(item["left_checkpoint_id"]), -float(item["cosine"]))):
        add(
            f"| {row['left_checkpoint_id']} | {row['left_file']} vs {row['right_file']} | {sim(row['cosine'])} | {'yes' if row['near_duplicate_screen'] else 'no'} |"
        )
    add("")
    if near:
        add("The 0.98 screen flags leakage. It is not an acceptance threshold. Removing a flagged partner still leaves any lower-scoring photograph of that checkpoint in the gallery.")
        add("")
    else:
        add("No same-checkpoint pair reached the 0.98 near-duplicate screen.")
        add("")
    add("Highest different-checkpoint baseline pairs inside Red Fort:")
    add("")
    add("| Pair | Cosine |")
    add("| --- | ---: |")
    for row in cross_pairs[:8]:
        add(
            f"| {row['left_checkpoint_id']} / {row['left_file']} vs {row['right_checkpoint_id']} / {row['right_file']} | {sim(row['cosine'])} |"
        )
    add("")
    add("## Method")
    add("")
    add("1. Keep only `red-fort` rows whose collection is `existing` or `added` and whose file is present.")
    add("2. Embed each file with the cached model. Encode one image at a time.")
    add("3. For each image strategy, remove the query. Optionally also remove same-checkpoint photographs whose baseline cosine with the query is at least 0.98.")
    add("4. Score the remaining photographs. Rank checkpoints by max or by mean. Break an equal score by checkpoint id, in alphabetical order.")
    add("5. Apply 0.97 and 0.05 only to those image-image scores.")
    add("6. For the text tower, rank the ten fixed prompts for every photograph. Do not remove anything from a gallery, because this strategy does not use reference photographs.")
    add("")
    add("Checkpoints with one photograph cannot support a correct retrieval result under this design. Their trials still count toward the all-query false-accept rate.")
    add("")
    add("## Results")
    add("")
    add("Image retrieval, query removed, production rule:")
    add("")
    add("| Strategy | Exclusion | Top-1 correct | Accepted and correct | False accepts among evaluable | Rejections among evaluable | False accepts among all photos |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for strategy, _key, _aggregate in IMAGE_STRATEGIES:
        for exclusion in ("held_out_self", "held_out_self_and_near_duplicates"):
            row = find_summary(summaries, strategy, exclusion)
            add(
                f"| {strategy} | {exclusion} | {count_line(row, 'top1_correct')} | {count_line(row, 'accepted_correct')} | {count_line(row, 'false_accept_evaluable')} | {count_line(row, 'rejected_evaluable')} | {count_line(row, 'false_accept_all')} |"
            )
    add("")
    add(
        f"Text prompts, top-1 only: {text_all['top1_correct']}/{text_all['all_queries']} of all Red Fort photographs, and {text_sibling['top1_correct']}/{text_sibling['all_queries']} of the photographs whose checkpoint has a sibling. The production acceptance rule was not applied."
    )
    add("")
    add("Baseline trials where another photograph of the true checkpoint remains:")
    add("")
    add("| Query | Top checkpoint | True-checkpoint score | Next checkpoint | Margin | Outcome |")
    add("| --- | --- | ---: | --- | ---: | --- |")
    for trial in baseline:
        if not trial["evaluable"]:
            continue
        add(
            f"| {trial['query_checkpoint_id']} / {trial['query_file']} | {trial['top1_checkpoint_id']} ({sim(trial['best_similarity'])}) | {sim(trial['true_checkpoint_similarity'])} | {trial['second_checkpoint_id']} ({sim(trial['second_similarity'])}) | {sim(trial['margin'])} | {trial['outcome']} |"
        )
    add("")
    add("Baseline trials with no remaining photograph of the true checkpoint:")
    add("")
    add("| Query | Highest other checkpoint | Score | Margin | Outcome |")
    add("| --- | --- | ---: | ---: | --- |")
    for trial in baseline:
        if trial["evaluable"]:
            continue
        add(
            f"| {trial['query_checkpoint_id']} / {trial['query_file']} | {trial['top1_checkpoint_id']} | {sim(trial['best_similarity'])} | {sim(trial['margin'])} | {trial['outcome']} |"
        )
    add("")
    add("Text prompts:")
    add("")
    text_trials = [trial for trial in trials if trial["strategy"] == "text_zeroshot"]
    text_right = [trial for trial in text_trials if trial["top1_correct"]]
    text_wrong = [trial for trial in text_trials if not trial["top1_correct"]]
    if text_right:
        named = ", ".join(f"{trial['query_checkpoint_id']} / {trial['query_file']}" for trial in text_right)
        add(f"Text prompts ranked the true checkpoint first for: {named}.")
        add("")
    if not text_wrong:
        add("Every Red Fort photograph was closest to its own checkpoint prompt.")
        add("")
    else:
        add("The other photographs ranked a different checkpoint first:")
        add("")
        add("| Query | Chosen checkpoint | Chosen score | True-checkpoint score |")
        add("| --- | --- | ---: | ---: |")
        for trial in text_wrong:
            add(
                f"| {trial['query_checkpoint_id']} / {trial['query_file']} | {trial['top1_checkpoint_id']} | {sim(trial['best_similarity'])} | {sim(trial['true_checkpoint_similarity'])} |"
            )
        add("")
    add("Where another image strategy changed the baseline outcome:")
    add("")
    changes = 0
    for trial in trials:
        if trial["strategy"] in {"baseline_max", "text_zeroshot"}:
            continue
        match = next(
            item
            for item in trials
            if item["strategy"] == "baseline_max"
            and item["exclusion"] == trial["exclusion"]
            and item["query_file"] == trial["query_file"]
        )
        if match["outcome"] == trial["outcome"] and match["top1_checkpoint_id"] == trial["top1_checkpoint_id"]:
            continue
        if changes == 0:
            add("| Strategy | Exclusion | Query | Baseline | This strategy |")
            add("| --- | --- | --- | --- | --- |")
        changes += 1
        add(
            f"| {trial['strategy']} | {trial['exclusion']} | {trial['query_file']} | {match['top1_checkpoint_id']} / {match['outcome']} | {trial['top1_checkpoint_id']} / {trial['outcome']} |"
        )
    if changes == 0:
        add("No max-aggregation variant changed a baseline top checkpoint or a baseline outcome. Mean aggregation is included in that comparison.")
    add("")
    add("## What these results mean")
    add("")
    base_top1 = int(base_summary["top1_correct"])
    base_eval = int(base_summary["evaluable_queries"])
    base_accept = int(base_summary["accepted_correct"])
    base_false = int(base_summary["false_accept_all"])
    add(
        f"On the {base_eval} photographs that have another picture of the same checkpoint, full-frame retrieval ranks the right checkpoint first {base_top1} times and the production rule accepts {base_accept} of them. Across all {base_summary['all_queries']} photographs, the rule names the wrong checkpoint {base_false} times."
    )
    add("")
    accepted_names = [
        f"{trial['query_file']} at {sim(trial['best_similarity'])}"
        for trial in baseline
        if trial["outcome"] == "ranked_correct_accepted"
    ]
    wrong_rank = [
        f"{trial['query_file']} ranks {trial['top1_checkpoint_id']} at {sim(trial['best_similarity'])} and the true checkpoint at {sim(trial['true_checkpoint_similarity'])}"
        for trial in baseline
        if trial["evaluable"] and trial["outcome"] == "ranked_wrong_rejected"
    ]
    correct_rejected = [
        f"{trial['query_file']} at {sim(trial['true_checkpoint_similarity'])}"
        for trial in baseline
        if trial["outcome"] == "ranked_correct_rejected"
    ]
    if accepted_names:
        add("Accepted and correct: " + "; ".join(accepted_names) + ".")
        add("")
    if correct_rejected:
        add("Ranked correctly and rejected by the 0.97 rule: " + "; ".join(correct_rejected) + ".")
        add("")
    if wrong_rank:
        add("Ranked incorrectly and rejected, so the failure is the ranking rather than a false popup: " + "; ".join(wrong_rank) + ".")
        add("")
    moti_pair = next(row for row in same_pairs if row["left_checkpoint_id"] == "moti-masjid")
    add(
        f"The two Moti Masjid photographs score {sim(moti_pair['cosine'])} against each other, which is below both of their scores with Diwan-i-Khas. Two stored views are not enough when those views do not agree with each other."
    )
    add("")
    add(
        f"Removing the Rang Mahal pair that scores at or above {NEAR_DUPLICATE:.2f} leaves baseline top-1 at {near_summary['top1_correct']}/{near_summary['evaluable_queries']} and accepted-correct at {near_summary['accepted_correct']}/{near_summary['evaluable_queries']}. The two Lahori Gate accepts remain. The Rang Mahal near-duplicate accepts do not."
    )
    add("")
    better_rank = []
    better_accept = []
    for strategy, _key, _aggregate in IMAGE_STRATEGIES:
        if strategy == "baseline_max":
            continue
        row = find_summary(summaries, strategy, "held_out_self")
        if int(row["top1_correct"]) > base_top1:
            better_rank.append(strategy)
        if row["accepted_correct"] != "" and int(row["accepted_correct"]) > base_accept:
            better_accept.append(strategy)
    text_better = int(text_sibling["top1_correct"]) > base_top1
    if not better_rank and not better_accept and not text_better:
        add("None of the local alternatives ranked more of these sibling photographs correctly, and none were accepted correctly more often, than full-frame max retrieval. That comparison is inside the reference set. It does not show that the baseline would recognize a new phone photograph.")
    else:
        pieces = []
        if better_rank:
            pieces.append("higher top-1 on the sibling photographs: " + ", ".join(better_rank))
        if better_accept:
            pieces.append("more production-rule accepts: " + ", ".join(better_accept))
        if text_better:
            pieces.append(
                f"the text tower's top-1 on the sibling photographs was {text_sibling['top1_correct']}/{text_sibling['all_queries']}, against the baseline's {base_top1}/{base_eval}"
            )
        add(
            "Relative to full-frame max retrieval on this same reference set, the measured differences are: "
            + "; ".join(pieces)
            + ". A gain here is a reason to carry that pipeline into an independent phone test. It is not a reason to change the live service or the 0.97 and 0.05 rules."
        )
    add("")
    add("## What this data cannot establish")
    add("")
    add("- Whether a visitor's phone photograph of any Red Fort checkpoint would be ranked correctly or accepted. Every query above is another reference photograph, not a new capture.")
    add("- A recognition rate for Chhatta Chowk, Naubat Khana, Diwan-i-Am, Mumtaz Mahal, the hammam, or Shahi Burj. Each has one photograph, so leave-one-out removes the only labelled example.")
    add("- Whether more viewpoints would raise acceptance. The 17 shortlisted files were not downloaded and were not scored.")
    add("- A safe threshold below 0.97. No cutoff was fitted, and there is no separate set of lookalike non-matches from the fort.")
    add("- Recognition of a carving, painting, inscription, or other detail. The labels are whole checkpoints.")
    add("- Live-camera behavior. The trials are still photographs.")
    add("- A comparison with a larger visual model. No other weights are cached, and this run does not download any.")
    add("")
    add("## Is a different model or training justified?")
    add("")
    add("Fine-tuning is not justified on this set. There are 16 labelled photographs, six checkpoints have a single photograph, and there is no independent test set. A model trained on these files would be fit to the gallery, and the task forbids training on future test photographs.")
    add("")
    add("A separate pretrained classifier was not tested. ImageNet labels do not name these buildings, and no other checkpoint is cached locally. The text tower of this same ViT-B-32 was the pretrained alternative that could be run without a download. Its top-1 figures are reported above. They do not by themselves justify swapping it in for the image-retrieval service.")
    add("")
    add("Mean aggregation changes a checkpoint's own score only when at least two of its photographs remain. That applies to Diwan-i-Khas and Rang Mahal. Other checkpoints still have multi-photo rivals, so averaging those rivals can change which wrong checkpoint ranks first. On this run, mean aggregation kept the same eight correct top ranks, turned the two Rang Mahal near-duplicate accepts into rejections, and did not make Moti Masjid rank itself first.")
    add("")
    add("## Independent phone photographs")
    add("")
    add("Keep new photographs in `local-recognition/red-fort-independent/<checkpoint-id>/`. Do not copy them into `public/references`, `local-recognition/references`, or `reference_manifest.csv` until a separate evaluation is finished. Do not train on them.")
    add("")
    add("Use two sessions. Session `reference_candidate` may later be considered for the gallery. Session `query` is the test and stays out of the gallery. Decide the session when the photograph is taken. Do not move a file from one session to the other after seeing a score.")
    add("")
    add("Capture with the rear camera, original resolution, JPEG, and no beauty or portrait filter. Save the uncropped frame. For each front view, save one portrait frame and one landscape frame.")
    add("")
    add("The smallest set that addresses the current gaps:")
    add("")
    add("| Checkpoint | Why these frames | Minimum query frames, session `query` |")
    add("| --- | --- | --- |")
    add("| Lahori Gate | Only checkpoint the current rule accepted from a second stored view | Front, side, distant, close-up, and one partial occlusion. At least two lighting conditions. |")
    add("| Diwan-i-Khas | Ranks first on stored alternates and stays under 0.97 | Front, side, distant, close-up. Include one frame shared with the Diwan-i-Am courtyard. |")
    add("| Diwan-i-Am | One stored photograph, and it is the hall nearest Diwan-i-Khas | Front, rear or side, distant, close-up. One frame that also shows Diwan-i-Khas, labelled as Diwan-i-Am. |")
    add("| Moti Masjid | Stored views rank Diwan-i-Khas first | The mosque alone, close and distant; one side; one partial occlusion; one courtyard frame where Diwan-i-Khas is also visible, labelled as Moti Masjid. |")
    add("")
    add("For each of those four, repeat the front and the confusing shared frame in a second lighting condition. The six one-photograph checkpoints need their own later pair of sessions. A single new download cannot be both the new reference and the test.")
    add("")
    add("Each file needs a row in a copy of `red_fort_independent_capture_template.csv`:")
    add("")
    add("- `checkpoint_id`: one of the ten ids already in the Red Fort catalog.")
    add("- `view`: `front`, `side`, `distant`, `close_up`, or `partial`.")
    add("- `lighting`: `direct_sun`, `open_shade`, `overcast`, `night`, or `mixed`.")
    add("- `distance_band`: `near`, `mid`, or `far`.")
    add("- `occlusion`: `none`, `partial`, or `heavy`.")
    add("- `intended_subject_only`: `yes` when the named checkpoint fills the decision, `no` when another named structure is deliberately visible.")
    add("- `confusing_neighbor`: the other checkpoint id, or blank.")
    add("- `session`: `reference_candidate` or `query`.")
    add("- `photographer`, `device`, and `captured_at`: recorded, not invented after the fact.")
    add("- `source_note`: how the photographer knows which building is in the frame.")
    add("")
    add("Moti Masjid versus Diwan-i-Khas needs three kinds of query frame: each building alone, and both in one frame with the intended subject written down before scoring. The same pattern applies to Diwan-i-Am versus Diwan-i-Khas.")
    add("")
    add("## Next smallest experiment")
    add("")
    add("Photograph the four-checkpoint query set above. Freeze the current pipeline: full-frame OpenCLIP ViT-B-32, max cosine per checkpoint, 0.97 and 0.05. Score each query photograph once against the gallery as it exists today, with the query file absent from that gallery. Record rank, score, margin, and accept or reject. Do not add the query files to the gallery, do not change the prompts or the crops after seeing the scores, and do not train.")
    add("")
    add("That run answers whether a real second view of Lahori Gate still clears the rule, and whether Moti Masjid is still closer to Diwan-i-Khas than to itself. Those are the uncertainties this reference-set experiment cannot close.")
    add("")
    add("## Files written")
    add("")
    add("- `local-recognition/red_fort_experiment.py`")
    add("- `local-recognition/red_fort_recognition_experiment.md`")
    add("- `local-recognition/red_fort_experiment_inventory.csv`")
    add("- `local-recognition/red_fort_experiment_trials.csv`")
    add("- `local-recognition/red_fort_experiment_summary.csv`")
    add("- `local-recognition/red_fort_experiment_pairs.csv`")
    add("- `local-recognition/red_fort_independent_capture_template.csv`")
    add("")
    if REPORT_PATH.name in PROTECTED:
        raise RuntimeError("Refusing to overwrite a protected report.")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_inventory(photos: list[Photograph]) -> None:
    rows = [
        {
            "destination_slug": DESTINATION,
            "checkpoint_id": photo.checkpoint_id,
            "checkpoint_name": photo.name,
            "collection": photo.collection,
            "filename": photo.path.name,
            "path": str(photo.path),
            "width": photo.width,
            "height": photo.height,
            "bytes": photo.byte_size,
            "sha256": photo.sha256,
        }
        for photo in photos
    ]
    write_csv(INVENTORY_PATH, rows)


def write_capture_template() -> None:
    if CAPTURE_TEMPLATE_PATH.name in PROTECTED:
        raise RuntimeError("Refusing to overwrite a protected file.")
    fieldnames = [
        "destination_slug",
        "checkpoint_id",
        "filename",
        "view",
        "lighting",
        "distance_band",
        "occlusion",
        "intended_subject_only",
        "confusing_neighbor",
        "photographer",
        "device",
        "captured_at",
        "session",
        "source_note",
    ]
    with CAPTURE_TEMPLATE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()


def main() -> None:
    import time

    import torch

    photos, shortlist, notes, extras = load_manifest()
    if len(photos) < 1:
        raise RuntimeError("No Red Fort photographs were found.")
    device = select_device()
    model, preprocess, tokenizer = load_model(device)
    started = time.perf_counter()
    embed_photos(model, preprocess, device, photos)
    image_seconds = time.perf_counter() - started
    text_started = time.perf_counter()
    text_vectors = embed_prompts(model, tokenizer, device)
    text_seconds = time.perf_counter() - text_started
    embed_seconds = image_seconds
    self_scores = [cosine(photo.embeddings["baseline"], photo.embeddings["baseline"]) for photo in photos]
    image_trials = build_image_trials(photos)
    text_trials = build_text_trials(photos, text_vectors)
    trials = image_trials + text_trials
    pairs = pair_rows(photos)
    summaries = summary_rows(trials)
    write_inventory(photos)
    write_csv(TRIALS_PATH, trials)
    write_csv(SUMMARY_PATH, summaries)
    write_csv(PAIRS_PATH, pairs)
    write_capture_template()
    write_report(
        photos,
        shortlist,
        notes,
        extras,
        pairs,
        trials,
        summaries,
        device.type,
        embed_seconds,
        text_seconds,
        min(self_scores),
        max(self_scores),
    )
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    baseline = find_summary(summaries, "baseline_max", "held_out_self")
    print(
        f"Red Fort photos: {len(photos)}. Device: {device.type}. "
        f"Baseline top-1 {baseline['top1_correct']}/{baseline['evaluable_queries']}, "
        f"accepted {baseline['accepted_correct']}/{baseline['evaluable_queries']}. "
        f"Report: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
