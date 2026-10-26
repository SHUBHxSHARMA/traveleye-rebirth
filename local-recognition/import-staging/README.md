# Staging reference photographs

Put a candidate here before it is considered for the local gallery. Validation reads files and writes a report. It does not download photographs, and it does not change files under `references\` or the Next.js `public\references` folder.

## Folder

```text
import-staging\<destination-slug>\<checkpoint-id>\<filename>.jpg
import-staging\<destination-slug>\<checkpoint-id>\<filename>.jpg.json
```

Use a destination slug and checkpoint id that already exist in the guide, such as `red-fort\moti-masjid`. JPEG, PNG, and WebP files are accepted.

## Metadata

The JSON file sits beside the image and uses the image name plus `.json`. Fill these fields from the source page:

- `source_page`
- `author`
- `licence`
- `licence_url`

Leave a field out when the source page does not provide it. The validator will mark the file for review. Do not invent an author or a licence. `metadata.example.json` shows the field names only. It is not attribution for a real photograph.

## PowerShell

```powershell
$stage = "E:\TravelEye-Rebirth\local-recognition\import-staging\red-fort\moti-masjid"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item "C:\path\to\your-photo.jpg" -Destination $stage

@'
{
  "source_page": "https://commons.wikimedia.org/wiki/File:Your_File.jpg",
  "author": "Name as given on the source page",
  "licence": "CC BY-SA 4.0",
  "licence_url": "https://creativecommons.org/licenses/by-sa/4.0"
}
'@ | Set-Content -Encoding utf8 "$stage\your-photo.jpg.json"

& "E:\TravelEye-Rebirth\local-recognition\.venv\Scripts\python.exe" "E:\TravelEye-Rebirth\local-recognition\import_staging.py"
```

The report is written to `import-staging\validation_report.txt` and `import-staging\validation_report.csv`.

`passed` means the file decoded, the checkpoint id is valid, the required metadata is present, and the bytes are not already in the gallery. `needs_review` means attribution is incomplete, or the image looks like another file by a coarse average hash. That hash warning does not reject a distinct viewpoint. `failed` means the file is unreadable, too large, an unsupported format, an unknown checkpoint, or an exact SHA-256 duplicate.

Passing validation does not add the photograph to the live gallery.
