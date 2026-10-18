"""OCR backends: RapidOCR by default, Indra OCR when its models are installed."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .config import indra_dir


@dataclass(frozen=True, slots=True)
class TextLine:
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float = 1.0


class OCRUnavailable(RuntimeError):
    """Raised when the requested OCR backend is not installed."""


def _indra_ready() -> bool:
    try:
        import indra_ocr  # noqa: F401
    except ImportError:
        return False
    folder = indra_dir()
    required = ("det.onnx", "rec.onnx", "meta.json")
    return all((folder / name).exists() for name in required)


def resolve_backend(name: str = "auto") -> str:
    name = (name or "auto").lower()
    if name == "auto":
        return "indra" if _indra_ready() else "rapidocr"
    if name in {"rapid", "rapidocr"}:
        return "rapidocr"
    if name == "indra":
        if not _indra_ready():
            raise OCRUnavailable(
                "Indra OCR is not installed or its models are missing. "
                "Run: python scripts/download_models.py --with-indra"
            )
        return "indra"
    raise ValueError(f"unknown OCR backend: {name}")


@lru_cache(maxsize=1)
def _rapid():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _rapid_lines(image_bgr: np.ndarray) -> list[TextLine]:
    result, _elapsed = _rapid()(image_bgr)
    lines: list[TextLine] = []
    for item in result or []:
        box, text, score = item[0], item[1], float(item[2])
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        lines.append(
            TextLine(str(text), (min(xs), min(ys), max(xs), max(ys)), score)
        )
    return lines


@lru_cache(maxsize=2)
def _indra(model_path: str, threads: int):
    import indra_ocr

    return indra_ocr.load(path=model_path, threads=threads)


def _indra_lines(image_bgr: np.ndarray) -> list[TextLine]:
    folder = indra_dir()
    threads = int(os.getenv("REDACT_INDRA_THREADS", "2"))
    converter = _indra(str(folder), threads)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        if not cv2.imwrite(str(temp_path), image_bgr):
            raise OCRUnavailable("could not prepare the image for Indra OCR")
        lines: list[TextLine] = []
        for item in converter.convert(str(temp_path)):
            page = item[1] if isinstance(item, tuple) else item
            for line in page.lines:
                x0, y0, x1, y1 = line.box
                lines.append(
                    TextLine(str(line.text), (x0, y0, x1, y1), float(line.conf))
                )
        return lines
    finally:
        temp_path.unlink(missing_ok=True)


def ocr_lines(image_bgr: np.ndarray, backend: str = "auto") -> list[TextLine]:
    selected = resolve_backend(backend)
    if selected == "indra":
        return _indra_lines(image_bgr)
    return _rapid_lines(image_bgr)


def backend_status() -> dict[str, object]:
    return {
        "auto": resolve_backend("auto"),
        "rapidocr": True,
        "indra": _indra_ready(),
        "indra_dir": str(indra_dir()),
    }
