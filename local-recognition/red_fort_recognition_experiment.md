# Red Fort recognition experiment

Run date: 2026-10-27.

This run reads the Red Fort photographs already on disk and the cached OpenCLIP ViT-B-32 weights. It does not change the scanner, the frontend, the API, the production thresholds, or the live gallery. It does not download photographs or weights, and it does not train a model.

## What was tested

Model: OpenCLIP ViT-B-32, QuickGELU enabled, OpenAI image mean and standard deviation, bicubic resize on the shortest side. Weights: `E:\TravelEye-Rebirth\local-recognition\cache\models--timm--vit_base_patch32_clip_224.openai\snapshots\a6f597a30f7b82c51704746581f9a4e41421e878\open_clip_model.safetensors`. Device: cuda. The four image representations took 6.1 seconds. The ten text prompts took 0.1 seconds.

The image strategies use one shared leave-one-image-out procedure inside `red-fort` only. The query photograph is removed before scoring. A checkpoint score is either the maximum cosine among that checkpoint's remaining photographs, which is the production aggregation, or the mean of those cosines. A result is accepted only when the best score is at least 0.97 and the margin to the next checkpoint is at least 0.05. Those two numbers are imported from `recognition.py`. They were not changed, and no other cutoff was selected.

The representations, fixed before looking at these scores, are:

- `baseline_max` and `baseline_mean`: the production full-frame preprocess.
- `multicrop_max`: the mean of three normalized embeddings, from the full frame, a centered 80 percent crop, and a centered 60 percent crop, then normalized again.
- `center60_max`: the centered 60 percent crop only.
- `unsharp_max`: an unsharp mask (radius 1.5, percent 120, threshold 2) and then the production preprocess.
- `text_zeroshot`: the same model's text tower. Each checkpoint has one prompt, `a photograph of {name} at the Red Fort in Delhi`. The display names are the names already in `recognition.DESTINATIONS`. Image-text cosine is not judged with the 0.97 rule, because that rule was set for image-image retrieval and these scores sit on a different scale.

A query is evaluable for image retrieval when at least one other photograph of its true checkpoint remains. Top-1 accuracy, accepted-match rate, and rejection rate use that evaluable set as the denominator. False-accept rate is also reported over every Red Fort photograph, because a single-photo checkpoint can still be given the wrong name. Correct ranking means the true checkpoint has the highest score. Accepted recognition means the production rule also accepts that checkpoint. Those are different outcomes.

Self-similarity of each baseline embedding against itself was 1.000000 to 1.000000. Those values are a normalization check. They are not recognition trials.

## Inventory

Manifest rows for Red Fort with a local file: 16. Shortlist rows with no local file, excluded from scoring: 17. Exact SHA-256 duplicates: 0.

| Checkpoint | Photographs on disk | Shortlisted, not on disk | Evaluable for retrieval |
| --- | ---: | ---: | --- |
| Lahori Gate | 2 | 0 | yes |
| Chhatta Chowk | 1 | 3 | no, the only photograph would be the query |
| Naubat Khana (Drum House) | 1 | 3 | no, the only photograph would be the query |
| Diwan-i-Am (Hall of Public Audience) | 1 | 3 | no, the only photograph would be the query |
| Diwan-i-Khas (Hall of Private Audience) | 3 | 0 | yes |
| Mumtaz Mahal | 1 | 2 | no, the only photograph would be the query |
| Rang Mahal (Palace of Colours) | 3 | 0 | yes |
| Moti Masjid (Pearl Mosque) | 2 | 0 | yes |
| Royal Hammam (Baths) | 1 | 3 | no, the only photograph would be the query |
| Shahi Burj (Royal Tower) | 1 | 3 | no, the only photograph would be the query |

JPEG files in the same folder as these references that are not listed in the manifest were not embedded:

- `delhi-fort.jpg`

Same-checkpoint baseline pairs:

| Checkpoint | Files | Cosine | Near-duplicate screen (0.98) |
| --- | --- | ---: | --- |
| diwan-i-khas | diwan-i-khas-1.jpg vs diwan-i-khas-2.jpg | 0.9227 | no |
| diwan-i-khas | diwan-i-khas-2.jpg vs diwan-i-khas-3.jpg | 0.8667 | no |
| diwan-i-khas | diwan-i-khas-1.jpg vs diwan-i-khas-3.jpg | 0.8262 | no |
| lahori-gate | lahori-gate-user.jpg vs lahori-gate.jpg | 0.9711 | no |
| moti-masjid | moti-masjid-1.jpg vs moti-masjid-2.jpg | 0.6820 | no |
| rang-mahal | rang-mahal-user.jpg vs rang-mahal.jpg | 0.9947 | yes |
| rang-mahal | rang-mahal-2.jpg vs rang-mahal-user.jpg | 0.8602 | no |
| rang-mahal | rang-mahal-2.jpg vs rang-mahal.jpg | 0.8596 | no |

The 0.98 screen flags leakage. It is not an acceptance threshold. Removing a flagged partner still leaves any lower-scoring photograph of that checkpoint in the gallery.

Highest different-checkpoint baseline pairs inside Red Fort:

| Pair | Cosine |
| --- | ---: |
| lahori-gate / lahori-gate.jpg vs naubat-khana / naubat-khana.jpg | 0.8886 |
| lahori-gate / lahori-gate-user.jpg vs naubat-khana / naubat-khana.jpg | 0.8808 |
| diwan-i-am / diwan-i-am.jpg vs diwan-i-khas / diwan-i-khas-2.jpg | 0.8738 |
| diwan-i-am / diwan-i-am.jpg vs diwan-i-khas / diwan-i-khas-1.jpg | 0.8611 |
| diwan-i-khas / diwan-i-khas-2.jpg vs shahi-burj / shahi-burj.jpg | 0.8484 |
| hammam / hammam.jpg vs shahi-burj / shahi-burj.jpg | 0.8467 |
| diwan-i-khas / diwan-i-khas-3.jpg vs rang-mahal / rang-mahal.jpg | 0.8334 |
| naubat-khana / naubat-khana.jpg vs rang-mahal / rang-mahal.jpg | 0.8300 |

## Method

1. Keep only `red-fort` rows whose collection is `existing` or `added` and whose file is present.
2. Embed each file with the cached model. Encode one image at a time.
3. For each image strategy, remove the query. Optionally also remove same-checkpoint photographs whose baseline cosine with the query is at least 0.98.
4. Score the remaining photographs. Rank checkpoints by max or by mean. Break an equal score by checkpoint id, in alphabetical order.
5. Apply 0.97 and 0.05 only to those image-image scores.
6. For the text tower, rank the ten fixed prompts for every photograph. Do not remove anything from a gallery, because this strategy does not use reference photographs.

Checkpoints with one photograph cannot support a correct retrieval result under this design. Their trials still count toward the all-query false-accept rate.

## Results

Image retrieval, query removed, production rule:

| Strategy | Exclusion | Top-1 correct | Accepted and correct | False accepts among evaluable | Rejections among evaluable | False accepts among all photos |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_max | held_out_self | 8/10 | 4/10 | 0/10 | 6/10 | 0/16 |
| baseline_max | held_out_self_and_near_duplicates | 8/10 | 2/10 | 0/10 | 8/10 | 0/16 |
| baseline_mean | held_out_self | 8/10 | 2/10 | 0/10 | 8/10 | 0/16 |
| baseline_mean | held_out_self_and_near_duplicates | 8/10 | 2/10 | 0/10 | 8/10 | 0/16 |
| multicrop_max | held_out_self | 7/10 | 4/10 | 0/10 | 6/10 | 0/16 |
| multicrop_max | held_out_self_and_near_duplicates | 5/10 | 2/10 | 0/10 | 8/10 | 0/16 |
| center60_max | held_out_self | 6/10 | 2/10 | 0/10 | 8/10 | 0/16 |
| center60_max | held_out_self_and_near_duplicates | 4/10 | 0/10 | 0/10 | 10/10 | 0/16 |
| unsharp_max | held_out_self | 8/10 | 2/10 | 0/10 | 8/10 | 0/16 |
| unsharp_max | held_out_self_and_near_duplicates | 6/10 | 0/10 | 0/10 | 10/10 | 0/16 |

Text prompts, top-1 only: 2/16 of all Red Fort photographs, and 2/10 of the photographs whose checkpoint has a sibling. The production acceptance rule was not applied.

Baseline trials where another photograph of the true checkpoint remains:

| Query | Top checkpoint | True-checkpoint score | Next checkpoint | Margin | Outcome |
| --- | --- | ---: | --- | ---: | --- |
| lahori-gate / lahori-gate-user.jpg | lahori-gate (0.9711) | 0.9711 | naubat-khana (0.8808) | 0.0903 | ranked_correct_accepted |
| lahori-gate / lahori-gate.jpg | lahori-gate (0.9711) | 0.9711 | naubat-khana (0.8886) | 0.0826 | ranked_correct_accepted |
| diwan-i-khas / diwan-i-khas-1.jpg | diwan-i-khas (0.9227) | 0.9227 | diwan-i-am (0.8611) | 0.0616 | ranked_correct_rejected |
| diwan-i-khas / diwan-i-khas-2.jpg | diwan-i-khas (0.9227) | 0.9227 | diwan-i-am (0.8738) | 0.0489 | ranked_correct_rejected |
| diwan-i-khas / diwan-i-khas-3.jpg | diwan-i-khas (0.8667) | 0.8667 | rang-mahal (0.8334) | 0.0334 | ranked_correct_rejected |
| rang-mahal / rang-mahal-2.jpg | rang-mahal (0.8602) | 0.8602 | diwan-i-khas (0.8177) | 0.0425 | ranked_correct_rejected |
| rang-mahal / rang-mahal-user.jpg | rang-mahal (0.9947) | 0.9947 | diwan-i-khas (0.8280) | 0.1667 | ranked_correct_accepted |
| rang-mahal / rang-mahal.jpg | rang-mahal (0.9947) | 0.9947 | diwan-i-khas (0.8334) | 0.1613 | ranked_correct_accepted |
| moti-masjid / moti-masjid-1.jpg | diwan-i-khas (0.7755) | 0.6820 | diwan-i-am (0.7666) | 0.0088 | ranked_wrong_rejected |
| moti-masjid / moti-masjid-2.jpg | diwan-i-khas (0.8291) | 0.6820 | diwan-i-am (0.7805) | 0.0486 | ranked_wrong_rejected |

Baseline trials with no remaining photograph of the true checkpoint:

| Query | Highest other checkpoint | Score | Margin | Outcome |
| --- | --- | ---: | ---: | --- |
| chhatta-chowk / chhatta-chowk.jpg | diwan-i-khas | 0.8003 | 0.0381 | not_evaluable_rejected |
| naubat-khana / naubat-khana.jpg | lahori-gate | 0.8886 | 0.0586 | not_evaluable_rejected |
| diwan-i-am / diwan-i-am.jpg | diwan-i-khas | 0.8738 | 0.0676 | not_evaluable_rejected |
| mumtaz-mahal / mumtaz-mahal.jpg | hammam | 0.4837 | 0.0023 | not_evaluable_rejected |
| hammam / hammam.jpg | shahi-burj | 0.8467 | 0.0247 | not_evaluable_rejected |
| shahi-burj / shahi-burj.jpg | diwan-i-khas | 0.8484 | 0.0018 | not_evaluable_rejected |

Text prompts:

Text prompts ranked the true checkpoint first for: diwan-i-khas / diwan-i-khas-2.jpg, moti-masjid / moti-masjid-2.jpg.

The other photographs ranked a different checkpoint first:

| Query | Chosen checkpoint | Chosen score | True-checkpoint score |
| --- | --- | ---: | ---: |
| lahori-gate / lahori-gate-user.jpg | rang-mahal | 0.3244 | 0.3235 |
| lahori-gate / lahori-gate.jpg | rang-mahal | 0.3150 | 0.3148 |
| chhatta-chowk / chhatta-chowk.jpg | diwan-i-am | 0.3257 | 0.3147 |
| naubat-khana / naubat-khana.jpg | rang-mahal | 0.3329 | 0.3174 |
| diwan-i-am / diwan-i-am.jpg | rang-mahal | 0.3503 | 0.3433 |
| diwan-i-khas / diwan-i-khas-1.jpg | moti-masjid | 0.2985 | 0.2854 |
| diwan-i-khas / diwan-i-khas-3.jpg | moti-masjid | 0.3341 | 0.3339 |
| mumtaz-mahal / mumtaz-mahal.jpg | diwan-i-am | 0.2326 | 0.2139 |
| rang-mahal / rang-mahal-2.jpg | diwan-i-khas | 0.3472 | 0.3215 |
| rang-mahal / rang-mahal-user.jpg | hammam | 0.3493 | 0.3334 |
| rang-mahal / rang-mahal.jpg | hammam | 0.3499 | 0.3363 |
| moti-masjid / moti-masjid-1.jpg | naubat-khana | 0.2952 | 0.2743 |
| hammam / hammam.jpg | rang-mahal | 0.3294 | 0.3118 |
| shahi-burj / shahi-burj.jpg | rang-mahal | 0.3213 | 0.2817 |

Where another image strategy changed the baseline outcome:

| Strategy | Exclusion | Query | Baseline | This strategy |
| --- | --- | --- | --- | --- |
| baseline_mean | held_out_self | rang-mahal-user.jpg | rang-mahal / ranked_correct_accepted | rang-mahal / ranked_correct_rejected |
| baseline_mean | held_out_self | rang-mahal.jpg | rang-mahal / ranked_correct_accepted | rang-mahal / ranked_correct_rejected |
| baseline_mean | held_out_self | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | diwan-i-am / ranked_wrong_rejected |
| baseline_mean | held_out_self | shahi-burj.jpg | diwan-i-khas / not_evaluable_rejected | hammam / not_evaluable_rejected |
| multicrop_max | held_out_self | diwan-i-khas-3.jpg | diwan-i-khas / ranked_correct_rejected | rang-mahal / ranked_wrong_rejected |
| multicrop_max | held_out_self | mumtaz-mahal.jpg | hammam / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| multicrop_max | held_out_self | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | diwan-i-am / ranked_wrong_rejected |
| center60_max | held_out_self | lahori-gate-user.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| center60_max | held_out_self | lahori-gate.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| center60_max | held_out_self | chhatta-chowk.jpg | diwan-i-khas / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| center60_max | held_out_self | diwan-i-khas-3.jpg | diwan-i-khas / ranked_correct_rejected | rang-mahal / ranked_wrong_rejected |
| center60_max | held_out_self | mumtaz-mahal.jpg | hammam / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| center60_max | held_out_self | rang-mahal-2.jpg | rang-mahal / ranked_correct_rejected | naubat-khana / ranked_wrong_rejected |
| center60_max | held_out_self | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | diwan-i-am / ranked_wrong_rejected |
| center60_max | held_out_self | shahi-burj.jpg | diwan-i-khas / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| unsharp_max | held_out_self | lahori-gate-user.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| unsharp_max | held_out_self | lahori-gate.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| unsharp_max | held_out_self | mumtaz-mahal.jpg | hammam / not_evaluable_rejected | moti-masjid / not_evaluable_rejected |
| unsharp_max | held_out_self | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | hammam / ranked_wrong_rejected |
| unsharp_max | held_out_self | hammam.jpg | shahi-burj / not_evaluable_rejected | diwan-i-khas / not_evaluable_rejected |
| baseline_mean | held_out_self_and_near_duplicates | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | diwan-i-am / ranked_wrong_rejected |
| baseline_mean | held_out_self_and_near_duplicates | shahi-burj.jpg | diwan-i-khas / not_evaluable_rejected | hammam / not_evaluable_rejected |
| multicrop_max | held_out_self_and_near_duplicates | diwan-i-khas-3.jpg | diwan-i-khas / ranked_correct_rejected | rang-mahal / ranked_wrong_rejected |
| multicrop_max | held_out_self_and_near_duplicates | mumtaz-mahal.jpg | hammam / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| multicrop_max | held_out_self_and_near_duplicates | rang-mahal-user.jpg | rang-mahal / ranked_correct_rejected | diwan-i-khas / ranked_wrong_rejected |
| multicrop_max | held_out_self_and_near_duplicates | rang-mahal.jpg | rang-mahal / ranked_correct_rejected | diwan-i-khas / ranked_wrong_rejected |
| multicrop_max | held_out_self_and_near_duplicates | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | diwan-i-am / ranked_wrong_rejected |
| center60_max | held_out_self_and_near_duplicates | lahori-gate-user.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| center60_max | held_out_self_and_near_duplicates | lahori-gate.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| center60_max | held_out_self_and_near_duplicates | chhatta-chowk.jpg | diwan-i-khas / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| center60_max | held_out_self_and_near_duplicates | diwan-i-khas-3.jpg | diwan-i-khas / ranked_correct_rejected | rang-mahal / ranked_wrong_rejected |
| center60_max | held_out_self_and_near_duplicates | mumtaz-mahal.jpg | hammam / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| center60_max | held_out_self_and_near_duplicates | rang-mahal-2.jpg | rang-mahal / ranked_correct_rejected | naubat-khana / ranked_wrong_rejected |
| center60_max | held_out_self_and_near_duplicates | rang-mahal-user.jpg | rang-mahal / ranked_correct_rejected | diwan-i-khas / ranked_wrong_rejected |
| center60_max | held_out_self_and_near_duplicates | rang-mahal.jpg | rang-mahal / ranked_correct_rejected | diwan-i-khas / ranked_wrong_rejected |
| center60_max | held_out_self_and_near_duplicates | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | diwan-i-am / ranked_wrong_rejected |
| center60_max | held_out_self_and_near_duplicates | shahi-burj.jpg | diwan-i-khas / not_evaluable_rejected | rang-mahal / not_evaluable_rejected |
| unsharp_max | held_out_self_and_near_duplicates | lahori-gate-user.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| unsharp_max | held_out_self_and_near_duplicates | lahori-gate.jpg | lahori-gate / ranked_correct_accepted | lahori-gate / ranked_correct_rejected |
| unsharp_max | held_out_self_and_near_duplicates | mumtaz-mahal.jpg | hammam / not_evaluable_rejected | moti-masjid / not_evaluable_rejected |
| unsharp_max | held_out_self_and_near_duplicates | rang-mahal-user.jpg | rang-mahal / ranked_correct_rejected | diwan-i-khas / ranked_wrong_rejected |
| unsharp_max | held_out_self_and_near_duplicates | rang-mahal.jpg | rang-mahal / ranked_correct_rejected | diwan-i-khas / ranked_wrong_rejected |
| unsharp_max | held_out_self_and_near_duplicates | moti-masjid-1.jpg | diwan-i-khas / ranked_wrong_rejected | hammam / ranked_wrong_rejected |
| unsharp_max | held_out_self_and_near_duplicates | hammam.jpg | shahi-burj / not_evaluable_rejected | diwan-i-khas / not_evaluable_rejected |

## What these results mean

On the 10 photographs that have another picture of the same checkpoint, full-frame retrieval ranks the right checkpoint first 8 times and the production rule accepts 4 of them. Across all 16 photographs, the rule names the wrong checkpoint 0 times.

Accepted and correct: lahori-gate-user.jpg at 0.9711; lahori-gate.jpg at 0.9711; rang-mahal-user.jpg at 0.9947; rang-mahal.jpg at 0.9947.

Ranked correctly and rejected by the 0.97 rule: diwan-i-khas-1.jpg at 0.9227; diwan-i-khas-2.jpg at 0.9227; diwan-i-khas-3.jpg at 0.8667; rang-mahal-2.jpg at 0.8602.

Ranked incorrectly and rejected, so the failure is the ranking rather than a false popup: moti-masjid-1.jpg ranks diwan-i-khas at 0.7755 and the true checkpoint at 0.6820; moti-masjid-2.jpg ranks diwan-i-khas at 0.8291 and the true checkpoint at 0.6820.

The two Moti Masjid photographs score 0.6820 against each other, which is below both of their scores with Diwan-i-Khas. Two stored views are not enough when those views do not agree with each other.

Removing the Rang Mahal pair that scores at or above 0.98 leaves baseline top-1 at 8/10 and accepted-correct at 2/10. The two Lahori Gate accepts remain. The Rang Mahal near-duplicate accepts do not.

None of the local alternatives ranked more of these sibling photographs correctly, and none were accepted correctly more often, than full-frame max retrieval. That comparison is inside the reference set. It does not show that the baseline would recognize a new phone photograph.

## What this data cannot establish

- Whether a visitor's phone photograph of any Red Fort checkpoint would be ranked correctly or accepted. Every query above is another reference photograph, not a new capture.
- A recognition rate for Chhatta Chowk, Naubat Khana, Diwan-i-Am, Mumtaz Mahal, the hammam, or Shahi Burj. Each has one photograph, so leave-one-out removes the only labelled example.
- Whether more viewpoints would raise acceptance. The 17 shortlisted files were not downloaded and were not scored.
- A safe threshold below 0.97. No cutoff was fitted, and there is no separate set of lookalike non-matches from the fort.
- Recognition of a carving, painting, inscription, or other detail. The labels are whole checkpoints.
- Live-camera behavior. The trials are still photographs.
- A comparison with a larger visual model. No other weights are cached, and this run does not download any.

## Is a different model or training justified?

Fine-tuning is not justified on this set. There are 16 labelled photographs, six checkpoints have a single photograph, and there is no independent test set. A model trained on these files would be fit to the gallery, and the task forbids training on future test photographs.

A separate pretrained classifier was not tested. ImageNet labels do not name these buildings, and no other checkpoint is cached locally. The text tower of this same ViT-B-32 was the pretrained alternative that could be run without a download. Its top-1 figures are reported above. They do not by themselves justify swapping it in for the image-retrieval service.

Mean aggregation changes a checkpoint's own score only when at least two of its photographs remain. That applies to Diwan-i-Khas and Rang Mahal. Other checkpoints still have multi-photo rivals, so averaging those rivals can change which wrong checkpoint ranks first. On this run, mean aggregation kept the same eight correct top ranks, turned the two Rang Mahal near-duplicate accepts into rejections, and did not make Moti Masjid rank itself first.

## Independent phone photographs

Keep new photographs in `local-recognition/red-fort-independent/<checkpoint-id>/`. Do not copy them into `public/references`, `local-recognition/references`, or `reference_manifest.csv` until a separate evaluation is finished. Do not train on them.

Use two sessions. Session `reference_candidate` may later be considered for the gallery. Session `query` is the test and stays out of the gallery. Decide the session when the photograph is taken. Do not move a file from one session to the other after seeing a score.

Capture with the rear camera, original resolution, JPEG, and no beauty or portrait filter. Save the uncropped frame. For each front view, save one portrait frame and one landscape frame.

The smallest set that addresses the current gaps:

| Checkpoint | Why these frames | Minimum query frames, session `query` |
| --- | --- | --- |
| Lahori Gate | Only checkpoint the current rule accepted from a second stored view | Front, side, distant, close-up, and one partial occlusion. At least two lighting conditions. |
| Diwan-i-Khas | Ranks first on stored alternates and stays under 0.97 | Front, side, distant, close-up. Include one frame shared with the Diwan-i-Am courtyard. |
| Diwan-i-Am | One stored photograph, and it is the hall nearest Diwan-i-Khas | Front, rear or side, distant, close-up. One frame that also shows Diwan-i-Khas, labelled as Diwan-i-Am. |
| Moti Masjid | Stored views rank Diwan-i-Khas first | The mosque alone, close and distant; one side; one partial occlusion; one courtyard frame where Diwan-i-Khas is also visible, labelled as Moti Masjid. |

For each of those four, repeat the front and the confusing shared frame in a second lighting condition. The six one-photograph checkpoints need their own later pair of sessions. A single new download cannot be both the new reference and the test.

Each file needs a row in a copy of `red_fort_independent_capture_template.csv`:

- `checkpoint_id`: one of the ten ids already in the Red Fort catalog.
- `view`: `front`, `side`, `distant`, `close_up`, or `partial`.
- `lighting`: `direct_sun`, `open_shade`, `overcast`, `night`, or `mixed`.
- `distance_band`: `near`, `mid`, or `far`.
- `occlusion`: `none`, `partial`, or `heavy`.
- `intended_subject_only`: `yes` when the named checkpoint fills the decision, `no` when another named structure is deliberately visible.
- `confusing_neighbor`: the other checkpoint id, or blank.
- `session`: `reference_candidate` or `query`.
- `photographer`, `device`, and `captured_at`: recorded, not invented after the fact.
- `source_note`: how the photographer knows which building is in the frame.

Moti Masjid versus Diwan-i-Khas needs three kinds of query frame: each building alone, and both in one frame with the intended subject written down before scoring. The same pattern applies to Diwan-i-Am versus Diwan-i-Khas.

## Next smallest experiment

Photograph the four-checkpoint query set above. Freeze the current pipeline: full-frame OpenCLIP ViT-B-32, max cosine per checkpoint, 0.97 and 0.05. Score each query photograph once against the gallery as it exists today, with the query file absent from that gallery. Record rank, score, margin, and accept or reject. Do not add the query files to the gallery, do not change the prompts or the crops after seeing the scores, and do not train.

That run answers whether a real second view of Lahori Gate still clears the rule, and whether Moti Masjid is still closer to Diwan-i-Khas than to itself. Those are the uncertainties this reference-set experiment cannot close.

## Files written

- `local-recognition/red_fort_experiment.py`
- `local-recognition/red_fort_recognition_experiment.md`
- `local-recognition/red_fort_experiment_inventory.csv`
- `local-recognition/red_fort_experiment_trials.csv`
- `local-recognition/red_fort_experiment_summary.csv`
- `local-recognition/red_fort_experiment_pairs.csv`
- `local-recognition/red_fort_independent_capture_template.csv`
