"""Local redaction UI."""

from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Paths
from .engine import process
from .html_report import write_report
from .ocr import OCRUnavailable, backend_status

OUTPUT_DIR = Path.home() / ".redact" / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR = OUTPUT_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).resolve().parent / "static"


def cleanup_old_uploads() -> None:
    """Remove original uploads left by older versions. Keep outputs and reports."""
    for path in OUTPUT_DIR.iterdir():
        if not path.is_file():
            continue
        name = path.name
        if ".redacted." in name or name.endswith(".report.json"):
            continue
        path.unlink(missing_ok=True)


cleanup_old_uploads()
for old in JOBS_DIR.iterdir():
    if old.is_dir() and old.stat().st_mtime < time.time() - 7 * 24 * 3600:
        shutil.rmtree(old, ignore_errors=True)

ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
MAX_UPLOAD = 25 * 1024 * 1024
MAX_PDF_PAGES = 100

app = FastAPI(title="redact", version="0.2.3")


class ApplyRequest(BaseModel):
    job: str
    selected: list[str]
    ocr: str = "auto"


def _safe_job(job: str) -> Path:
    folder = (JOBS_DIR / Path(job).name).resolve()
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    return folder
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/healthz")
def health() -> dict[str, object]:
    return {"ok": True, "ocr": backend_status()}


@app.post("/api/scan")
async def scan(file: UploadFile = File(...), ocr: str = Form("auto")) -> JSONResponse:
    """Detect findings and keep the source for a second, reviewable pass."""
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail="unsupported file type")
    payload = await file.read(MAX_UPLOAD + 1)
    if len(payload) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="file too large (max 25 MB)")

    job = uuid.uuid4().hex
    folder = JOBS_DIR / job
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / f"source{suffix}"
    source.write_bytes(payload)
    if suffix == ".pdf":
        import pymupdf

        try:
            with pymupdf.open(source) as document:
                if document.page_count > MAX_PDF_PAGES:
                    raise HTTPException(status_code=413, detail="PDF has too many pages (max 100)")
        except HTTPException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        except Exception as exc:
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPException(status_code=400, detail="not a readable PDF") from exc

    started = time.perf_counter()
    try:
        result = process(
            source,
            dry_run=True,
            face_model=Paths.default().face_model,
            ocr_backend=ocr,
        )
    except OCRUnavailable as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    elapsed = round((time.perf_counter() - started) * 1000)
    return JSONResponse(
        {
            "job": job,
            "preview": f"/files/jobs/{job}/source{suffix}",
            "is_pdf": suffix == ".pdf",
            "counts": result.counts,
            "counts_total": len(result.findings),
            "findings": [finding.to_dict() for finding in result.findings],
            "warnings": result.warnings,
            "took_ms": elapsed,
        }
    )


@app.post("/api/apply")
def apply_selection(request: ApplyRequest) -> JSONResponse:
    """Redact only the findings accepted in review."""
    if not request.selected:
        raise HTTPException(status_code=400, detail="select at least one finding")
    folder = _safe_job(request.job)
    sources = list(folder.glob("source.*"))
    if not sources:
        raise HTTPException(status_code=404, detail="source is no longer available")
    source = sources[0]
    suffix = source.suffix.lower()
    output = folder / f"redacted{suffix if suffix != '.pdf' else '.pdf'}"
    report = folder / "report.json"
    html_report = folder / "report.html"
    try:
        result = process(
            source,
            output_path=output,
            report_path=report,
            face_model=Paths.default().face_model,
            ocr_backend=request.ocr,
            selected=set(request.selected),
        )
        write_report(result, html_report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        source.unlink(missing_ok=True)
    return JSONResponse(
        {
            "download": f"/files/jobs/{request.job}/{output.name}",
            "preview": f"/files/jobs/{request.job}/{output.name}",
            "report": f"/files/jobs/{request.job}/{report.name}",
            "html_report": f"/files/jobs/{request.job}/{html_report.name}",
            "is_pdf": suffix == ".pdf",
            "counts": result.counts,
            "counts_total": len(result.findings),
            "findings": [finding.to_dict() for finding in result.findings],
            "warnings": result.warnings,
        }
    )


@app.post("/api/redact")
async def redact(file: UploadFile = File(...), ocr: str = Form("auto")) -> JSONResponse:
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail="unsupported file type")

    payload = await file.read(MAX_UPLOAD + 1)
    if len(payload) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="file too large (max 25 MB)")

    job = uuid.uuid4().hex
    source = OUTPUT_DIR / f"{job}{suffix}"
    source.write_bytes(payload)
    if suffix == ".pdf":
        import pymupdf

        try:
            with pymupdf.open(source) as document:
                if document.page_count > MAX_PDF_PAGES:
                    raise HTTPException(
                        status_code=413, detail="PDF has too many pages (max 100)"
                    )
        except HTTPException:
            source.unlink(missing_ok=True)
            raise
        except Exception as exc:
            source.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="not a readable PDF") from exc
    output = OUTPUT_DIR / f"{job}.redacted{suffix if suffix != '.pdf' else '.pdf'}"
    report = OUTPUT_DIR / f"{job}.report.json"
    html_report = OUTPUT_DIR / f"{job}.report.html"

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        source.unlink(missing_ok=True)
    write_report(result, html_report)
    elapsed = round((time.perf_counter() - started) * 1000)

    return JSONResponse(
        {
            "download": f"/files/{output.name}",
            "preview": f"/files/{output.name}",
            "report": f"/files/{report.name}",
            "html_report": f"/files/{html_report.name}",
            "is_pdf": suffix == ".pdf",
            "counts": result.counts,
            "counts_total": len(result.findings),
            "findings": [finding.to_dict() for finding in result.findings],
            "warnings": result.warnings,
            "took_ms": elapsed,
        }
    )


@app.get("/files/jobs/{job}/{name}")
def download_job(job: str, name: str) -> FileResponse:
    folder = _safe_job(job)
    target = (folder / Path(name).name).resolve()
    if not target.is_relative_to(folder) or not target.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(target, filename=target.name)


@app.get("/files/{name}")
def download(name: str) -> FileResponse:
    safe = Path(name).name
    path = OUTPUT_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, filename=safe)
