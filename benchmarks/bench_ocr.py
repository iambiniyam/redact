"""Compare OCR backends on the synthetic PII form."""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2

from redact.detectors import detect_lines
from redact.ocr import OCRUnavailable, ocr_lines

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pii_form.png"
EXPECTED = {"name", "email", "phone", "card", "passport", "address", "date_of_birth"}


def measure(backend: str, runs: int = 5) -> dict:
    image = cv2.imread(str(FIXTURE), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"cannot read {FIXTURE}")

    ocr_lines(image, backend=backend)
    timings = []
    lines = []
    for _ in range(runs):
        started = time.perf_counter()
        lines = ocr_lines(image, backend=backend)
        timings.append((time.perf_counter() - started) * 1000)

    findings = detect_lines(lines)
    kinds = {finding.kind for finding in findings}
    confidence = sum(line.confidence for line in lines) / len(lines) if lines else 0
    return {
        "backend": backend,
        "lines": len(lines),
        "avg_confidence": round(confidence, 3),
        "mean_ms": round(sum(timings) / len(timings), 1),
        "p95_ms": round(sorted(timings)[-1], 1),
        "found": sorted(kinds & EXPECTED),
        "recall": round(len(kinds & EXPECTED) / len(EXPECTED), 3),
        "extra": sorted(kinds - EXPECTED),
    }


def main() -> None:
    rows = []
    for backend in ("rapidocr", "indra"):
        try:
            rows.append(measure(backend))
        except (OCRUnavailable, ImportError) as exc:
            rows.append({"backend": backend, "error": str(exc)})
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
