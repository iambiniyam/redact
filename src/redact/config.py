"""Paths and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def model_dir() -> Path:
    return Path(os.getenv("REDACT_MODEL_DIR", str(Path.home() / ".redact" / "models")))


@dataclass(slots=True)
class Paths:
    face_model: Path

    @classmethod
    def default(cls) -> "Paths":
        return cls(face_model=model_dir() / "face_detection_yunet.onnx")


DEFAULT_DPI = 200
FACE_MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
