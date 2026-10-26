"""Download verified Wikimedia Commons photographs for the local evaluation set.

Each file in APPROVED was checked against a Commons file page or category
listing and the imageinfo licence and author fields. Files are stored unchanged.
The Next.js application is not modified.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADDED_ROOT = ROOT / "references"
MANIFEST_PATH = ROOT / "reference_manifest.csv"
EXISTING_DIR = (
    ROOT.parent
    / "Travel_Eye-main (1)"
    / "Travel_Eye-main"
    / "travel-eye"
    / "public"
    / "references"
)
USER_AGENT = "TravelEyeLocalResearch/1.0 (educational reference collection)"

# title, destination, checkpoint, viewpoint note confirmed from the file title,
# description, or Commons category. Not inferred beyond those fields.
APPROVED: list[tuple[str, str, str, str]] = [
    (
        "File:The symmetrical front view of Taj Mahal.jpg",
        "taj-mahal",
        "taj-mahal-mausoleum",
        "Front view. The file description calls it a sunset view of the Taj Mahal.",
    ),
    (
        "File:Agra-Taj Mahal-45-Suedostseite-2018-gje.jpg",
        "taj-mahal",
        "taj-mahal-mausoleum",
        "Southeast side. The filename says Suedostseite and the description says the Taj Mahal in Agra.",
    ),
    (
        "File:Tajmahal side view Mausoleum in Agra 9.jpg",
        "taj-mahal",
        "taj-mahal-mausoleum",
        "Side view. The description says it is a side view of the mausoleum in Agra.",
    ),
    (
        "File:A view of Taj Mahal from the Mosque adjacent.jpg",
        "taj-mahal",
        "taj-mahal-mausoleum",
        "View from the adjacent mosque, as stated in the filename and description.",
    ),
    (
        "File:Qutb Minar from a Low-Angle View, Delhi, India.jpg",
        "qutub-minar",
        "qutub-minar-tower",
        "Low-angle view of the tower. The description describes the fluted shaft and balconies.",
    ),
    (
        "File:Blue sky behind Qutb Minar.jpg",
        "qutub-minar",
        "qutub-minar-tower",
        "The description says this is a picture of Qutb Minar.",
    ),
    (
        "File:Qutb Minar seen from Qutb Complex.jpg",
        "qutub-minar",
        "qutub-minar-tower",
        "The description says the Qutb Minar is visible from within the Qutb complex.",
    ),
    (
        "File:Iron Pillar View.jpg",
        "qutub-minar",
        "qutub-iron-pillar",
        "Listed in Category:Iron pillar.",
    ),
    (
        "File:Far view of iron pillar.jpg",
        "qutub-minar",
        "qutub-iron-pillar",
        "Far view. Listed in Category:Iron pillar.",
    ),
    (
        "File:Iron Pillar at Qutb Complex.jpg",
        "qutub-minar",
        "qutub-iron-pillar",
        "The description says the iron pillar at the Qutb complex, with the engraving.",
    ),
    (
        "File:Iron Pillar of Chandragupta II Vikramaditya.jpg",
        "qutub-minar",
        "qutub-iron-pillar",
        "Listed in Category:Iron pillar. The filename names that pillar.",
    ),
    (
        "File:Alai Darwaza Southern facade (2897540566).jpg",
        "qutub-minar",
        "qutub-alai-darwaza",
        "Southern facade, as stated in the filename and description.",
    ),
    (
        "File:Alai Darwaza View from the south-west (2896715777).jpg",
        "qutub-minar",
        "qutub-alai-darwaza",
        "South-west view, as stated in the filename and description.",
    ),
    (
        "File:East entrance of Alai Darwaza, Qutub Minar complex.jpg",
        "qutub-minar",
        "qutub-alai-darwaza",
        "East entrance. The description says the east entrance of Alai Darwaza.",
    ),
    (
        "File:001 Approaching the Stupa (33797177001).jpg",
        "sanchi-stupa",
        "sanchi-great-stupa",
        "Approach view. Listed in Category:Sanchi Stupa number 1. The description says Sanchi, Vidisha.",
    ),
    (
        "File:The Great Stupa of Sanchi, Raisen.jpg",
        "sanchi-stupa",
        "sanchi-great-stupa",
        "The description identifies the great stupa on the hill at Sanchi in Raisen district.",
    ),
    (
        "File:008 View of South and West Gates (33428100410).jpg",
        "sanchi-stupa",
        "sanchi-toranas",
        "South and west gates of Stupa 1. The file is listed in Category:Sanchi Stupa number 1.",
    ),
    (
        "File:003 Side View with Stupa Dome (33812402705).jpg",
        "sanchi-stupa",
        "sanchi-toranas",
        "Listed in Category:Sanchi gateways : East gateway of stupa 1.",
    ),
    (
        "File:A view from the southside of Kandariya temple 02.jpg",
        "khajuraho",
        "khajuraho-kandariya",
        "Another south-side file, distinct from the existing south-side photograph 01.",
    ),
    (
        "File:Kandariya Mahadeva Temple Backside View.jpg",
        "khajuraho",
        "khajuraho-kandariya",
        "Back view. The description identifies it as the largest temple of the Khajuraho group.",
    ),
    (
        "File:Khajuraho - Kandariya Mahadeva temple (3).jpg",
        "khajuraho",
        "khajuraho-kandariya",
        "The description names the Kandariya Mahadeva temple at Khajuraho.",
    ),
    (
        "File:Kandariya Mahadeva Temple at Sunset, Khajuraho, Madhya Pradesh.jpg",
        "khajuraho",
        "khajuraho-kandariya",
        "Sunset view. The description names the Kandariya Mahadeva Temple in Khajuraho.",
    ),
    (
        "File:Bazaar in Red Fort.jpg",
        "red-fort",
        "chhatta-chowk",
        "Listed in Category:Chhatta Chowk.",
    ),
    (
        "File:Chatta Chowk, Red Fort, Delhi.jpg",
        "red-fort",
        "chhatta-chowk",
        "The filename names Chatta Chowk at the Red Fort.",
    ),
    (
        "File:Chhatta Chowk market inside the Red fort 01.jpg",
        "red-fort",
        "chhatta-chowk",
        "The description says the Chhatta Chowk market inside the Red Fort.",
    ),
    (
        "File:Naubat Khana (Drum House) in Red Fort, Delhi (29140778193).jpg",
        "red-fort",
        "naubat-khana",
        "The description names Naubat Khana, the drum house, in the Red Fort.",
    ),
    (
        "File:Naubatkhana, Red Fort, Delhi - Side view.JPG",
        "red-fort",
        "naubat-khana",
        "Side view. The filename says Naubatkhana at the Red Fort.",
    ),
    (
        "File:Naubat Khana Red Fort Delhi.jpg",
        "red-fort",
        "naubat-khana",
        "The description says Naubat Khana in the Red Fort complex, Delhi.",
    ),
    (
        "File:Deewan-e-aam front.jpg",
        "red-fort",
        "diwan-i-am",
        "Front view. Listed in Category:Diwan-i-Am (Red Fort).",
    ),
    (
        "File:Diwan-i-Am (Red Fort) rear view.jpg",
        "red-fort",
        "diwan-i-am",
        "Rear view, from the filename. Listed with other Diwan-i-Am (Red Fort) files.",
    ),
    (
        "File:Diwan-i-Am (Red Fort), Delhi, India, 2018.jpg",
        "red-fort",
        "diwan-i-am",
        "Listed in Category:Diwan-i-Am (Red Fort).",
    ),
    (
        "File:Hammam khana in Red Fort, Delhi 01.jpg",
        "red-fort",
        "hammam",
        "The description says the hammam khana in the Red Fort, Delhi.",
    ),
    (
        "File:Hammam khana in Red Fort, Delhi 02.jpg",
        "red-fort",
        "hammam",
        "A second photograph whose description says the hammam khana in the Red Fort, Delhi.",
    ),
    (
        "File:Hammam - South-west View - Red Fort - Delhi 2014-05-13 3312.JPG",
        "red-fort",
        "hammam",
        "South-west view, from the filename, of the Red Fort hammam.",
    ),
    (
        "File:Delhi, India, Shahi Burj (Emperor's Tower), Red Fort.jpg",
        "red-fort",
        "shahi-burj",
        "The description says the Shahi Burj octagonal tower and pavilion at the Red Fort.",
    ),
    (
        "File:Shahi Burj Red Fort Delhi.jpg",
        "red-fort",
        "shahi-burj",
        "The description says Shahi Burj in the Red Fort complex, Delhi.",
    ),
    (
        "File:Shahi Burj in Red Fort, Delhi (29765860595).jpg",
        "red-fort",
        "shahi-burj",
        "The description says Shahi Burj in the Red Fort, Delhi.",
    ),
    (
        "File:Mumtaz Mahal Red Fort.jpg",
        "red-fort",
        "mumtaz-mahal",
        "The description identifies Mumtaz Mahal as a building facing the Yamuna inside the Red Fort.",
    ),
    (
        "File:Muntaz Mahal Red Fort Delhi India - panoramio.jpg",
        "red-fort",
        "mumtaz-mahal",
        "The description says Mumtaz Mahal at the Red Fort, Delhi. The filename spells Muntaz.",
    ),
]

EXISTING: list[tuple[str, str, str, str, str, str]] = [
    ("red-fort", "lahori-gate", "lahori-gate.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "lahori-gate", "lahori-gate-user.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "chhatta-chowk", "chhatta-chowk.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "naubat-khana", "naubat-khana.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "diwan-i-am", "diwan-i-am.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "diwan-i-khas", "diwan-i-khas-1.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "diwan-i-khas", "diwan-i-khas-2.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "diwan-i-khas", "diwan-i-khas-3.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "mumtaz-mahal", "mumtaz-mahal.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "rang-mahal", "rang-mahal.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "rang-mahal", "rang-mahal-user.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "rang-mahal", "rang-mahal-2.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "moti-masjid", "moti-masjid-1.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "moti-masjid", "moti-masjid-2.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "hammam", "hammam.jpg", "", "", "No author or licence is recorded in the project data."),
    ("red-fort", "shahi-burj", "shahi-burj.jpg", "", "", "No author or licence is recorded in the project data."),
    (
        "taj-mahal",
        "taj-mahal-mausoleum",
        "taj-mahal.jpg",
        "Yann Forget, edited by Jim Carter",
        "CC BY-SA 4.0",
        "Recorded in the project data as Taj Mahal (Edited).jpeg, Wikimedia Commons.",
    ),
    (
        "qutub-minar",
        "qutub-minar-tower",
        "qutb-minar.jpg",
        "IM3847",
        "CC BY-SA 4.0",
        "Recorded in the project data as A Potrait view of Qutub Minar.jpg, Wikimedia Commons.",
    ),
    (
        "qutub-minar",
        "qutub-iron-pillar",
        "iron-pillar-delhi.jpg",
        "pawan.kamrani",
        "CC BY-SA 4.0",
        "Recorded in the project data, Wikimedia Commons.",
    ),
    (
        "qutub-minar",
        "qutub-alai-darwaza",
        "alai-darwaza.jpg",
        "Alimallick",
        "CC BY-SA 3.0",
        "Recorded in the project data, Wikimedia Commons. File:Alai Darwaza.JPG on Commons has the same author and licence, so it was not downloaded again.",
    ),
    (
        "sanchi-stupa",
        "sanchi-great-stupa",
        "sanchi-stupa-1.jpg",
        "Bernard Gagnon",
        "CC BY-SA 3.0",
        "Recorded in the project data as Stupa 1, Sanchi 02.jpg, Wikimedia Commons.",
    ),
    (
        "khajuraho",
        "khajuraho-kandariya",
        "kandariya-mahadeva.jpg",
        "Ms Sarah Welch",
        "CC BY-SA 4.0",
        "Recorded in the project data as A view from the southside of Kandariya temple 01.jpg, Wikimedia Commons.",
    ),
]


def plain_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(unescape(text).split())


def load_metadata() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for name in ("commons_metadata.json", "commons_metadata_batch2.json"):
        payload = json.loads((ROOT / name).read_text(encoding="utf-8"))
        for page in payload.get("query", {}).get("pages", {}).values():
            title = page.get("title")
            info = (page.get("imageinfo") or [None])[0]
            if title and info:
                found[title] = info
    return found


def source_page(title: str) -> str:
    return "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="/()!:")


def attribution_requirement(licence: str) -> str:
    if "SA" in licence or "Share" in licence:
        return (
            "Credit the author, the file title, the Commons source page, and this licence. "
            "Adaptations must use the same licence."
        )
    return "Credit the author, the file title, the Commons source page, and this licence."


def safe_name(title: str) -> str:
    name = title.removeprefix("File:")
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def thumbnail_url(original: str, width: int) -> str:
    parsed = urllib.parse.urlparse(original)
    parts = [part for part in parsed.path.split("/") if part]
    filename = parts[-1]
    hashed = "/".join(parts[:-1]).replace("wikipedia/commons/", "wikipedia/commons/thumb/", 1)
    path = f"/{hashed}/{filename}/{width}px-{filename}"
    return urllib.parse.urlunparse(parsed._replace(path=path))


def download(url: str, destination: Path) -> str:
    """Save the original file. If Commons rate-limits it, save the 1280px thumbnail."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    candidates = [("original", url), ("wikimedia-1280px-thumbnail", thumbnail_url(url, 1280))]
    last_error: Exception | None = None
    for label, candidate in candidates:
        request = urllib.request.Request(candidate, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
            temporary.replace(destination)
            time.sleep(1.5)
            return label
        except urllib.error.HTTPError as exc:
            if temporary.exists():
                temporary.unlink()
            last_error = exc
            if exc.code != 429:
                break
            time.sleep(5)
    if last_error:
        raise last_error
    raise RuntimeError(f"Could not download {url}")


def main() -> None:
    metadata = load_metadata()
    rows: list[dict[str, str]] = []
    for slug, checkpoint_id, filename, author, licence, note in EXISTING:
        rows.append(
            {
                "collection": "existing",
                "destination_slug": slug,
                "checkpoint_id": checkpoint_id,
                "local_path": str(EXISTING_DIR / filename),
                "source_page": "",
                "direct_image_url": "",
                "author": author,
                "licence": licence,
                "licence_url": "",
                "stored_form": "existing-local-file",
                "viewpoint": "Already in the application reference set. Not replaced.",
                "attribution_requirements": note,
            }
        )

    for title, slug, checkpoint_id, viewpoint in APPROVED:
        info = metadata.get(title)
        if not info:
            raise SystemExit(f"Missing metadata for {title}")
        meta = info.get("extmetadata") or {}
        licence = plain_text((meta.get("LicenseShortName") or {}).get("value", ""))
        author = plain_text((meta.get("Artist") or {}).get("value", ""))
        licence_url = plain_text((meta.get("LicenseUrl") or {}).get("value", ""))
        lowered = licence.lower()
        if not author or "cc by" not in lowered or "nc" in lowered or "nd" in lowered:
            raise SystemExit(f"Refusing {title}: licence={licence!r} author={author!r}")
        filename = safe_name(title)
        destination = ADDED_ROOT / slug / checkpoint_id / filename
        thumbnails = {
            "Iron Pillar at Qutb Complex.jpg",
            "Iron Pillar of Chandragupta II Vikramaditya.jpg",
            "Alai Darwaza Southern facade (2897540566).jpg",
            "Alai Darwaza View from the south-west (2896715777).jpg",
            "East entrance of Alai Darwaza, Qutub Minar complex.jpg",
            "001 Approaching the Stupa (33797177001).jpg",
            "The Great Stupa of Sanchi, Raisen.jpg",
            "008 View of South and West Gates (33428100410).jpg",
            "003 Side View with Stupa Dome (33812402705).jpg",
            "A view from the southside of Kandariya temple 02.jpg",
            "Kandariya Mahadeva Temple Backside View.jpg",
        }
        if not destination.exists():
            print(f"not downloaded {title}")
            rows.append(
                {
                    "collection": "shortlist",
                    "destination_slug": slug,
                    "checkpoint_id": checkpoint_id,
                    "local_path": "",
                    "source_page": source_page(title),
                    "direct_image_url": info["url"],
                    "author": author,
                    "licence": licence,
                    "licence_url": licence_url,
                    "stored_form": "",
                    "viewpoint": viewpoint,
                    "attribution_requirements": attribution_requirement(licence),
                }
            )
            continue
        stored_form = "wikimedia-1280px-thumbnail" if destination.name in thumbnails else "original"
        print(f"saved {destination.name} ({destination.stat().st_size} bytes) {stored_form} {licence} {author}")
        rows.append(
            {
                "collection": "added",
                "destination_slug": slug,
                "checkpoint_id": checkpoint_id,
                "local_path": str(destination),
                "source_page": source_page(title),
                "direct_image_url": info["url"],
                "author": author,
                "licence": licence,
                "licence_url": licence_url,
                "stored_form": stored_form,
                "viewpoint": viewpoint,
                "attribution_requirements": attribution_requirement(licence),
            }
        )

    fieldnames = list(rows[0])
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"manifest {MANIFEST_PATH}")
    print(f"added_rows {sum(row['collection'] == 'added' for row in rows)}")
    print(f"shortlist_rows {sum(row['collection'] == 'shortlist' for row in rows)}")


if __name__ == "__main__":
    main()
