"""Local OpenCLIP recognition service.

Start from the existing virtual environment:

    local-recognition\\.venv\\Scripts\\python.exe local-recognition\\service.py

The process listens only on http://127.0.0.1:8765. Stop it with Ctrl+C.
It does not connect to the Next.js application.

TRAVELEYE_PORT changes the port. TRAVELEYE_MIN_SIMILARITY and
TRAVELEYE_MIN_MARGIN override the provisional acceptance checks.
The host stays on the loopback address.
"""

from __future__ import annotations

import os
import sys
from io import BytesIO

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from recognition import DESTINATIONS, MAX_PIXELS, RecognitionEngine

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def error(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"status": "error", "code": code, "message": message})


def create_app(engine: RecognitionEngine) -> FastAPI:
    app = FastAPI(title="Travel Eye local recognition", docs_url=None, redoc_url=None)

    @app.exception_handler(Exception)
    async def unexpected(_request, _exc) -> JSONResponse:
        return error(500, "The photograph could not be compared. Try again.", "error")

    @app.get("/health")
    def health() -> dict[str, object]:
        return engine.health()

    @app.post("/recognize")
    async def recognize(
        image: UploadFile | None = File(default=None),
        siteSlug: str = Form(default=""),
    ) -> JSONResponse:
        if image is None:
            return error(400, "Choose a photograph and a destination, then try again.", "invalid_image")
        slug = siteSlug.strip()
        if not slug:
            return error(400, "Choose a photograph and a destination, then try again.", "invalid_image")
        if slug not in DESTINATIONS:
            return error(404, "This destination is not in the guide.", "not_found")

        payload = await read_limited(image)
        if isinstance(payload, JSONResponse):
            return payload
        decoded = decode_image(payload, image.content_type or "")
        if isinstance(decoded, JSONResponse):
            return decoded
        try:
            vector = engine.embed_image(decoded)
            result = engine.match(slug, vector)
            del vector
        except Exception:
            return error(400, "That photograph could not be processed.", "invalid_image")
        finally:
            decoded.close()
        return JSONResponse(status_code=200, content=result)

    return app


async def read_limited(upload: UploadFile) -> bytes | JSONResponse:
    """Stop reading once the upload passes 8 MB, before any image decode."""
    chunks: list[bytes] = []
    size = 0
    try:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                return error(413, "That photograph is too large. Use an image under 8 MB.", "invalid_image")
            chunks.append(chunk)
    finally:
        await upload.close()
    if size == 0:
        return error(400, "The uploaded file is empty.", "invalid_image")
    return b"".join(chunks)


def decode_image(payload: bytes, content_type: str) -> Image.Image | JSONResponse:
    declared = content_type.split(";", 1)[0].strip().lower()
    if declared and not declared.startswith("image/"):
        return error(415, "That file is not a photograph. Use a JPG, PNG, or WebP image.", "invalid_image")
    try:
        image = Image.open(BytesIO(payload))
        if image.format not in ALLOWED_FORMATS:
            image.close()
            return error(415, "Use a JPG, PNG, or WebP photograph.", "invalid_image")
        if not image.width or not image.height or image.width * image.height > MAX_PIXELS:
            image.close()
            return error(400, "That image has no visible content.", "invalid_image")
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return error(400, "That file could not be read as an image.", "invalid_image")
    return image


def main() -> int:
    raw_port = os.environ.get("TRAVELEYE_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError:
        print("TRAVELEYE_PORT must be a whole number. The service did not start.", file=sys.stderr)
        return 1
    if not 1 <= port <= 65535:
        print("TRAVELEYE_PORT is outside the valid range. The service did not start.", file=sys.stderr)
        return 1
    try:
        engine = RecognitionEngine.load()
    except Exception as exc:
        print(f"Recognition service could not start: {exc}", file=sys.stderr)
        return 1
    app = create_app(engine)
    import uvicorn

    uvicorn.run(app, host=HOST, port=port, log_level="info", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
