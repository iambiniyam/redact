"""Document pipeline: render, detect, black out, and report."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import cv2
import pymupdf as fitz
import numpy as np

from .config import DEFAULT_DPI, Paths
from .detectors import TextLine, detect_faces, detect_lines, ocr_lines
from .findings import Finding

WARNING_RASTER = "PDF output is rasterized: the text layer and metadata are removed to prevent hidden-data leaks."


@dataclass(slots=True)
class ScanResult:
    input_path: Path
    output_path: Path | None
    pages: int
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return dict(Counter(finding.kind for finding in self.findings))

    def report(self) -> dict[str, object]:
        return {
            "tool": "redact-local",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "input": self.input_path.name,
            "output": self.output_path.name if self.output_path else None,
            "pages": self.pages,
            "counts": self.counts,
            "findings": [finding.to_dict() for finding in self.findings],
            "warnings": self.warnings,
        }


def _pdf_page_lines(page: fitz.Page, dpi: int) -> list[TextLine]:
    scale = dpi / 72.0
    lines: list[TextLine] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            lines.append(
                TextLine(text, (x0 * scale, y0 * scale, x1 * scale, y1 * scale), 1.0)
            )
    return lines


def _render_pdf_page(page: fitz.Page, dpi: int) -> np.ndarray:
    pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def _draw_masks(image: np.ndarray, findings: Iterable[Finding], pad: int = 2) -> np.ndarray:
    masked = image.copy()
    height, width = masked.shape[:2]
    for finding in findings:
        x0, y0, x1, y1 = finding.bbox
        left = max(0, int(x0) - pad)
        top = max(0, int(y0) - pad)
        right = min(width - 1, int(x1) + pad)
        bottom = min(height - 1, int(y1) + pad)
        cv2.rectangle(masked, (left, top), (right, bottom), (0, 0, 0), -1)
    return masked


def _filter(findings: list[Finding], kinds: set[str] | None) -> list[Finding]:
    if not kinds:
        return findings
    return [finding for finding in findings if finding.kind in kinds]


def scan_image(
    image: np.ndarray,
    page: int = 0,
    face_model: Path | None = None,
    kinds: set[str] | None = None,
) -> list[Finding]:
    findings = detect_lines(ocr_lines(image), page)
    findings += detect_faces(image, face_model, page=page)
    return _filter(findings, kinds)


def process(
    input_path: Path | str,
    output_path: Path | str | None = None,
    report_path: Path | str | None = None,
    dpi: int = DEFAULT_DPI,
    face_model: Path | None = None,
    kinds: set[str] | None = None,
    dry_run: bool = False,
) -> ScanResult:
    """Redact a PDF or image. Returns findings and writes the report."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    if face_model is None:
        face_model = Paths.default().face_model
    kind_set = {kind.strip().lower() for kind in kinds} if kinds else None

    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        return _process_pdf(input_path, output_path, report_path, dpi, face_model, kind_set, dry_run)
    return _process_image(input_path, output_path, report_path, face_model, kind_set, dry_run)


def _process_image(
    input_path: Path,
    output_path: Path | str | None,
    report_path: Path | str | None,
    face_model: Path | None,
    kinds: set[str] | None,
    dry_run: bool,
) -> ScanResult:
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read image: {input_path}")

    findings = scan_image(image, face_model=face_model, kinds=kinds)
    masked = _draw_masks(image, findings)

    result = ScanResult(input_path=input_path, output_path=None, pages=1, findings=findings)
    if not dry_run:
        target = Path(output_path) if output_path else input_path.with_name(
            f"{input_path.stem}.redacted{input_path.suffix or '.png'}"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(target), masked)
        result.output_path = target

    _write_report(result, report_path)
    return result


def _process_pdf(
    input_path: Path,
    output_path: Path | str | None,
    report_path: Path | str | None,
    dpi: int,
    face_model: Path | None,
    kinds: set[str] | None,
    dry_run: bool,
) -> ScanResult:
    document = fitz.open(input_path)
    redacted_pages: list[np.ndarray] = []
    findings: list[Finding] = []

    for index, page in enumerate(document):
        image = _render_pdf_page(page, dpi)
        lines = _pdf_page_lines(page, dpi)
        if sum(len(line.text) for line in lines) < 20:
            lines = ocr_lines(image)
        page_findings = detect_lines(lines, page=index)
        page_findings += detect_faces(image, face_model, page=index)
        page_findings = _filter(page_findings, kinds)
        findings.extend(page_findings)
        redacted_pages.append(_draw_masks(image, page_findings))

    pages = len(document)
    document.close()

    result = ScanResult(input_path=input_path, output_path=None, pages=pages, findings=findings)
    result.warnings.append(WARNING_RASTER)

    if not dry_run:
        target = Path(output_path) if output_path else input_path.with_name(
            f"{input_path.stem}.redacted.pdf"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        out = fitz.open()
        for image in redacted_pages:
            height, width = image.shape[:2]
            page = out.new_page(width=width * 72 / dpi, height=height * 72 / dpi)
            ok, buffer = cv2.imencode(".png", image)
            if not ok:
                raise RuntimeError("failed to encode redacted page")
            page.insert_image(page.rect, stream=buffer.tobytes())
        out.set_metadata({})
        out.save(str(target), garbage=3, deflate=True)
        out.close()
        result.output_path = target

    _write_report(result, report_path)
    return result


def _write_report(result: ScanResult, report_path: Path | str | None) -> None:
    payload = result.report()
    if report_path is None:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
