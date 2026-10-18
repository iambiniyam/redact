"""Local drag-and-drop redaction UI."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .config import Paths
from .engine import process

OUTPUT_DIR = Path.home() / ".redact" / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="redact", version="0.1.0")

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>redact: share the document, not your data</title>
<style>
  :root { color-scheme: light dark; --ink:#161a1d; --paper:#f7f5ef; --red:#b3261e; --line:#dcd7c8; }
  * { box-sizing:border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--paper); color:var(--ink); }
  header { max-width:780px; margin:0 auto; padding:32px 20px 8px; }
  h1 { font-size:2.1rem; letter-spacing:-.03em; margin:0 0 6px; }
  .sub { color:#5b665f; margin:0 0 18px; }
  main { max-width:780px; margin:0 auto; padding:0 20px 48px; }
  .card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:20px; box-shadow:0 6px 20px rgba(20,25,20,.05); margin-bottom:16px; }
  .drop { display:block; border:2px dashed #b9b3a2; border-radius:12px; padding:28px; text-align:center; cursor:pointer; background:#fbfaf4; }
  .drop:hover { border-color:var(--red); }
  input[type=file] { display:none; }
  button { background:var(--red); color:#fff; border:0; border-radius:10px; padding:12px 18px; font-weight:700; cursor:pointer; margin-top:14px; }
  button:disabled { opacity:.5; cursor:wait; }
  table { width:100%; border-collapse:collapse; margin-top:10px; font-size:.92rem; }
  th, td { text-align:left; padding:7px 6px; border-bottom:1px solid #eee7d8; }
  .pill { display:inline-block; background:#fdeceb; color:var(--red); border-radius:999px; padding:3px 10px; font-size:.78rem; font-weight:700; }
  .muted { color:#6c766f; font-size:.86rem; }
  a.dl { display:inline-block; margin-top:12px; background:#161a1d; color:#fff; text-decoration:none; padding:11px 16px; border-radius:9px; font-weight:700; }
  .err { color:#a3261e; }
  .preview { width:100%; border:1px solid #eee7d8; border-radius:10px; margin:12px 0; display:block; }
  iframe.preview { height:420px; }
</style>
</head>
<body>
<header>
  <h1>redact</h1>
  <p class="sub">Share the document, not your data. Everything runs on this machine. Nothing is uploaded.</p>
</header>
<main>
  <div class="card">
    <label class="drop" for="file">
      <strong>Choose a PDF or photo</strong><br>
      <span class="muted">IDs, contracts, medical forms, receipts, passports · JPG / PNG / PDF</span>
    </label>
    <input id="file" type="file" accept="application/pdf,image/*" required>
    <div><button id="go">Redact</button></div>
    <div id="status" class="muted"></div>
  </div>
  <div id="out"></div>
</main>
<script>
const fileInput = document.getElementById('file');
const go = document.getElementById('go');
const status = document.getElementById('status');
const out = document.getElementById('out');

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

go.addEventListener('click', async () => {
  const f = fileInput.files[0];
  if (!f) { status.textContent = 'Choose a file first.'; return; }
  go.disabled = true; status.textContent = 'Scanning locally...'; out.innerHTML = '';
  const fd = new FormData(); fd.append('file', f);
  try {
    const res = await fetch('/api/redact', { method: 'POST', body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || 'failed');
    const data = await res.json();
    const rows = data.findings.map(x => `<tr><td>${esc(x.kind)}</td><td>${esc(x.preview)}</td><td>${esc(x.source)}</td></tr>`).join('');
    const preview = data.is_pdf
      ? `<iframe class="preview" src="${data.preview}" title="redacted preview"></iframe>`
      : `<img class="preview" src="${data.preview}" alt="redacted preview">`;
    out.innerHTML = `<div class="card">
      <span class="pill">${data.counts_total} finding(s)</span>
      <h3>Redacted copy ready</h3>
      <p class="muted">Review the preview before sending. The report never contains the raw values.</p>
      ${preview}
      <table><thead><tr><th>Type</th><th>Preview</th><th>Source</th></tr></thead><tbody>${rows || '<tr><td colspan=3>No matches. Review manually.</td></tr>'}</tbody></table>
      <a class="dl" href="${data.download}" download>Download redacted file</a>
      <p class="muted">${esc(data.warnings.join(' '))}</p>
    </div>`;
    status.textContent = 'Done.';
  } catch (err) {
    status.innerHTML = `<span class="err">${esc(err.message)}</span>`;
  } finally {
    go.disabled = false;
  }
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/healthz")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/redact")
async def redact(file: UploadFile = File(...)) -> JSONResponse:
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}:
        raise HTTPException(status_code=400, detail="unsupported file type")

    job = uuid.uuid4().hex
    source = OUTPUT_DIR / f"{job}{suffix}"
    source.write_bytes(await file.read())
    output = OUTPUT_DIR / f"{job}.redacted{suffix if suffix != '.pdf' else '.pdf'}"

    try:
        result = process(source, output_path=output, face_model=Paths.default().face_model)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the UI
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse(
        {
            "download": f"/files/{output.name}",
            "preview": f"/files/{output.name}",
            "is_pdf": suffix == ".pdf",
            "counts": result.counts,
            "counts_total": len(result.findings),
            "findings": [finding.to_dict() for finding in result.findings],
            "warnings": result.warnings,
        }
    )


@app.get("/files/{name}")
def download(name: str) -> FileResponse:
    safe = Path(name).name
    path = OUTPUT_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, filename=safe)
