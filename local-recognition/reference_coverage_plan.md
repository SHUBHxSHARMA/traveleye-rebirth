# Reference-photo coverage plan

This inventory was taken from the five destination records, `reference_manifest.csv`, and `acceptance_audit.csv`. No photographs were downloaded, and the recognition thresholds, model, scanner, and galleries were not changed.

The minimum target below is 4 distinct viewpoints for each checkpoint: a principal face, a second side, a closer identifying detail, and a farther view. A second crop or export of the same photograph does not count toward that target. The target is a collection goal. It is not a new acceptance threshold.

## How the two galleries differ

The Next.js hash matcher uses only the files named in each checkpoint’s `referenceImageUrls`. That set has 22 files across 16 checkpoints.

The local OpenCLIP gallery uses the manifest rows whose collection is `existing` or `added` and whose file is on disk. That set has 42 files across 17 checkpoints. The 20 added files are not in the Next.js reference list. If the Python service is unavailable, the hash matcher cannot use them.

Nineteen manifest rows are `shortlist`. Their source pages, authors, and licences were recorded earlier. The files were not downloaded, so they are not usable references.

Nine checkpoints have no file in either gallery and no shortlist row. The scanner cannot name them.

No two of the 42 gallery files share a SHA-256 digest. One same-checkpoint pair scores 0.9947, which the acceptance audit treats as a near-duplicate. Red Fort files in the application have no recorded author or licence. This plan does not invent either.

Viewpoint notes for the added files come from the manifest text. This pass did not open every image again to rejudge the camera angle.

## Red Fort

| Checkpoint | App files | Local gallery | Shortlist not saved | Duplicate evidence | More photos |
| --- | --- | --- | --- | --- | --- |
| Lahori Gate | 2 | 2 | 0 | Pair scores 0.9711. Not a 0.98 near-duplicate. | 1 different angle, not another copy of the same front |
| Chhatta Chowk | 1 | 1 | 3 | None measured | Yes, to reach 4 distinct views |
| Naubat Khana | 1 | 1 | 3 | None measured | Yes, to reach 4 distinct views |
| Diwan-i-Am | 1 | 1 | 3 | None measured | Yes, to reach 4 distinct views |
| Diwan-i-Khas | 3 | 3 | 0 | None at the 0.98 screen. Highest sibling score 0.9227 | 1 view that is clearly unlike the other three |
| Mumtaz Mahal | 1 | 1 | 2 | None measured | Yes, to reach 4 distinct views |
| Rang Mahal | 3 | 3 | 0 | `rang-mahal.jpg` and `rang-mahal-user.jpg` score 0.9947 | 2 views that are not copies of that pair |
| Moti Masjid | 2 | 2 | 0 | None measured | Yes, 2 views that show the marble mosque itself |
| Royal Hammam | 1 | 1 | 3 | None measured | Yes, to reach 4 distinct views |
| Shahi Burj | 1 | 1 | 3 | None measured | Yes, to reach 4 distinct views |

Measured confusion, from leave-one-out inside Red Fort:

- Naubat Khana’s only photograph is closest to Lahori Gate at 0.8886.
- Diwan-i-Am’s only photograph is closest to Diwan-i-Khas at 0.8738.
- Shahi Burj’s only photograph is closest to Diwan-i-Khas at 0.8484, with the hammam at 0.8467.
- The hammam’s only photograph is closest to Shahi Burj at 0.8467.
- Both Moti Masjid photographs rank Diwan-i-Khas first, at 0.7755 and 0.8291.
- Diwan-i-Khas photographs rank Diwan-i-Khas first, at 0.8667 to 0.9227, and the 0.97 rule rejects them.
- Rang Mahal is accepted only through the 0.9947 pair. The third photograph ranks Rang Mahal first at about 0.860 and is rejected.
- The Red Fort Mumtaz Mahal’s nearest neighbour scores 0.4837. That is a low score, not evidence that a new photograph would match.

The current rule returns `no_match` for every one-photograph Red Fort query. That is a rejection, not a recognition of the neighbouring checkpoint.

## Taj Mahal

| Checkpoint | App files | Local gallery | Shortlist not saved | More photos |
| --- | --- | --- | --- | --- |
| Mausoleum | 1 | 5 | 0 | Count target is met. Do not add another similar front view. |
| Great Gate | 0 | 0 | 0 | 4, after a licensed source is verified |
| Charbagh | 0 | 0 | 0 | 4, after a licensed source is verified |
| Mosque and jawab | 0 | 0 | 0 | 4 photographs of the mosque and jawab, not more mausoleum views |

The five mausoleum files all rank the mausoleum first when one is held out. The best score is 0.9408, so the 0.97 rule rejects them. The manifest describes four added views: a front view called a sunset view, a southeast side, a side view, and a view from the adjacent mosque. The original application file’s camera angle was not re-verified. No other Taj checkpoint has a photograph, so a margin cannot be calculated at this destination.

The view from the adjacent mosque is labelled as a mausoleum photograph. It is not a reference for the mosque checkpoint.

## Qutub Minar

| Checkpoint | App files | Local gallery | Shortlist not saved | More photos |
| --- | --- | --- | --- | --- |
| Qutub Minar | 1 | 4 | 0 | Count target is met |
| Iron pillar | 1 | 5 | 0 | Count target is met |
| Alai Darwaza | 1 | 4 | 0 | Count target is met |
| Quwwat-ul-Islam mosque | 0 | 0 | 0 | 4, after a licensed source is verified |

Held-out queries for the tower, the iron pillar, and Alai Darwaza rank the correct checkpoint first inside Qutub Minar. Their scores stay below 0.97, from 0.7177 to 0.8786, so the rule rejects them. No pair reached the 0.98 duplicate screen.

One tower trial has Alai Darwaza as the second checkpoint at 0.8211, with a margin of 0.0078. That is a measured close call inside the destination, and it is still a rejection.

Alai Darwaza and Shahi Burj score 0.8916. That is the highest different-checkpoint score in the audit. It is a cross-destination comparison. The service does not compare those two when the visitor has selected only one destination.

## Sanchi Stupa

| Checkpoint | App files | Local gallery | Shortlist not saved | More photos |
| --- | --- | --- | --- | --- |
| Great Stupa | 1 | 3 | 0 | 1 view in which the dome, not a gateway, is the subject |
| Gateways | 0 | 2 | 0 | 2 views of a gateway, including a north gateway if a licensed file can be verified |
| Ashokan pillar | 0 | 0 | 0 | 4, after a licensed source is verified |
| Stupa 3 | 0 | 0 | 0 | 4, after a licensed source is verified |

The gateways have no application reference, so the hash matcher cannot name them. The local gallery has two files. The manifest places one with the south and west gates and the other with the east gateway of Stupa 1. A north gateway file was not found in the manifest.

Measured confusion: the original Great Stupa file, held out, ranks the gateways first at 0.8761 against the stupa at 0.8665. The south-and-west gates file, held out, ranks the Great Stupa first at 0.8761. The other stupa files and the other gateway file rank their own checkpoint first and are rejected by 0.97.

## Khajuraho

| Checkpoint | App files | Local gallery | Shortlist not saved | More photos |
| --- | --- | --- | --- | --- |
| Kandariya Mahadeva Temple | 1 | 3 | 2 | 1 front or other side, not a third south-side frame |
| Lakshmana Temple | 0 | 0 | 0 | 4, after a licensed source is verified |
| Vishvanatha Temple | 0 | 0 | 0 | 4, after a licensed source is verified |
| Parshvanatha Temple | 0 | 0 | 0 | 4, after a licensed source is verified |

The two south-side Kandariya files score 0.9274. The manifest calls the added file another south-side photograph, distinct from the existing south-side file. They are not a 0.98 near-duplicate. The back view’s best sibling score is 0.8500. All three rank Kandariya first and are rejected by 0.97. Khajuraho has no second photographed checkpoint, so the margin cannot be calculated. The two shortlist files are not in the gallery.

## What is measured, and what is not

Measured in `acceptance_audit.csv`:

- Correct checkpoint ranks first, then the 0.97 rule rejects the query: Taj mausoleum, Qutub Minar tower, iron pillar, Alai Darwaza inside Qutub Minar, Diwan-i-Khas, most Great Stupa and gateway queries, and Kandariya.
- Correct checkpoint does not rank first: both Moti Masjid photographs, the original Great Stupa photograph, and the south-and-west gates photograph.
- One near-duplicate pair: the two Rang Mahal files at 0.9947.
- No exact file duplicates among the 42 gallery files.
- No different-checkpoint pair reaches 0.97. The highest is Shahi Burj with Alai Darwaza at 0.8916, across destinations.

Not established:

- Whether a new visitor photograph would pass 0.97. These queries are other stored references.
- The camera angle of every original Red Fort file and of the original Taj Mahal file. Those angles are not recorded.
- Whether the 19 shortlist photographs show a different viewpoint from the file already on disk. They were not present for comparison.
- Author and licence for the Red Fort application photographs.

## Collection order

1. Moti Masjid. Add two licensed photographs whose subject is the white marble mosque, from different sides. The current pair loses to Diwan-i-Khas on ranking.
2. Great Stupa and the gateways together. Add one stupa view that does not make a gateway the main subject, and two gateway views that show the carved gate rather than the whole mound. Keep the gateways labelled `sanchi-toranas`, not `sanchi-great-stupa`.
3. Naubat Khana, Diwan-i-Am, Shahi Burj, and the hammam. Each has one photograph and a measured neighbour above 0.84. The verified shortlist is the first place to resume, after checking that each saved file is a different viewpoint. Do not treat a shortlist page as a gallery file until the image is saved.
4. Chhatta Chowk, then the Red Fort Mumtaz Mahal. Both have one photograph. Chhatta Chowk’s nearest measured neighbour is higher than Mumtaz Mahal’s.
5. Rang Mahal. Add two viewpoints that are not further copies of `rang-mahal.jpg`. Keep the existing near-duplicate; do not delete it in this plan.
6. Diwan-i-Khas. Add one view that is distinct from the three current hall photographs, because those three already sit close to Diwan-i-Am.
7. Checkpoints with no photograph: the Taj mosque and jawab, Quwwat-ul-Islam, Stupa 3, the Ashokan pillar, the three other Khajuraho temples, the Great Gate, and the charbagh. Collect these only from sources whose subject, author, and licence can be verified. A photograph of the whole complex is not a reference for one of these structures unless that structure is clearly the subject.
8. Leave the Taj mausoleum, Qutub Minar tower, iron pillar, Alai Darwaza, and Kandariya counts where they are unless a missing side is verified. More copies of the same side will not fill a gap. Lahori Gate needs a different angle only if one can be verified; it does not need another near-copy of the current pair.

Do not lower 0.97 or 0.05 to make the current gallery match itself. The acceptance audit already found that this closed set does not justify a threshold change.

## Files

- Created: `local-recognition/reference_coverage_plan.md`
- Created: `local-recognition/reference_coverage_inventory.csv`
- Read and left unchanged: the destination records, `reference_manifest.csv`, `acceptance_audit.csv`, `acceptance_audit_report.txt`, `expanded_leave_one_out.csv`, and `embedding_evaluation.csv`.
