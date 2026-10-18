"""Local redaction UI."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Paths
from .engine import process
from .ocr import OCRUnavailable, backend_status

OUTPUT_DIR = Path.home() / ".redact" / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).resolve().parent / "static"
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}

app = FastAPI(title="redact", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/healthz")
def health() -> dict[str, object]:
    return {"ok": True, "ocr": backend_status()}


@app.post("/api/redact")
async def redact(file: UploadFile = File(...), ocr: str = Form("auto")) -> JSONResponse:
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail="unsupported file type")

    job = uuid.uuid4().hex
    source = OUTPUT_DIR / f"{job}{suffix}"
    source.write_bytes(await file.read())
    output = OUTPUT_DIR / f"{job}.redacted{suffix if suffix != '.pdf' else '.pdf'}"
    report = OUTPUT_DIR / f"{job}.report.json"

    started = time.perf_counter()
    try:
        result = process(
            source,
            output_path=output,
            report_path=report,
            face_model=Paths.default().face_model,
            ocr_backend=ocr,
        )
    except OCRUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface a readable message to the UI
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    elapsed = round((time.perf_counter() - started) * 1000)

    return JSONResponse(
        {
            "download": f"/files/{output.name}",
            "preview": f"/files/{output.name}",
            "report": f"/files/{report.name}",
            "is_pdf": suffix == ".pdf",
            "counts": result.counts,
            "counts_total": len(result.findings),
            "findings": [finding.to_dict() for finding in result.findings],
            "warnings": result.warnings,
            "took_ms": elapsed,
        }
    )


@app.get("/files/{name}")
def download(name: str) -> FileResponse:
    safe = Path(name).name
    path = OUTPUT_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, filename=safe)
