"""Offline detectors: OCR, regex, labeled fields, faces."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import cv2
import numpy as np

from .findings import Finding
from .ocr import TextLine

EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,5}\d{2,4}(?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)")
IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

LABELED = re.compile(
    r"^\s*(full\s+name|name|patient|address|dob|date\s+of\s+birth|"
    r"passport(\s+(no|number))?|national\s+id|id\s+(no|number)|nin|ssn)\s*[:\-]",
    re.IGNORECASE,
)

_LABEL_KIND = {
    "name": "name",
    "full name": "name",
    "patient": "name",
    "address": "address",
    "dob": "date_of_birth",
    "date of birth": "date_of_birth",
    "passport": "passport",
    "passport no": "passport",
    "passport number": "passport",
    "national id": "national_id",
    "id no": "national_id",
    "id number": "national_id",
    "nin": "national_id",
    "ssn": "ssn",
}


def luhn(number: str) -> bool:
    digits = [int(ch) for ch in re.sub(r"\D", "", number)]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def iban_valid(candidate: str) -> bool:
    compact = re.sub(r"\s", "", candidate).upper()
    if not 15 <= len(compact) <= 34:
        return False
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(int(ch, 36)) if ch.isalpha() else ch for ch in rearranged)
    return int(digits) % 97 == 1


def _phone_valid(text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    return 7 <= len(digits) <= 15


def _bbox_union(boxes: Iterable[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    boxes = list(boxes)
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def detect_lines(lines: list[TextLine], page: int = 0) -> list[Finding]:
    """Find structured PII and labeled fields in OCR/text lines."""
    findings: list[Finding] = []
    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        label_match = LABELED.match(text)
        if label_match:
            label = re.sub(r"\s+", " ", label_match.group(1).lower()).strip()
            kind = _LABEL_KIND.get(label, "labeled")
            value = text[label_match.end():].strip() or text
            findings.append(Finding(kind, page, line.bbox, line.confidence, "label", value))
            continue

        for match in EMAIL.finditer(text):
            findings.append(Finding("email", page, line.bbox, line.confidence, "regex", match.group(0)))

        for match in CARD.finditer(text):
            value = match.group(0)
            if luhn(value):
                findings.append(Finding("card", page, line.bbox, line.confidence, "regex", value))

        for match in IBAN.finditer(text):
            value = match.group(0)
            if iban_valid(value):
                findings.append(Finding("iban", page, line.bbox, line.confidence, "regex", value))

        for match in SSN.finditer(text):
            findings.append(Finding("ssn", page, line.bbox, line.confidence, "regex", match.group(0)))

        # Phone last: avoid matching the digits inside an already-detected card.
        if not any(f.kind == "card" for f in findings if f.page == page and f.text and f.text in text):
            for match in PHONE.finditer(text):
                if _phone_valid(match.group(0)):
                    findings.append(Finding("phone", page, line.bbox, line.confidence, "regex", match.group(0)))

    return _dedupe(findings)


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, int, int, int]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.kind, finding.page, round(finding.bbox[0] / 4), round(finding.bbox[1] / 4))
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def detect_faces(
    image_bgr: np.ndarray, model_path: Path | None, min_score: float = 0.85, page: int = 0
) -> list[Finding]:
    """Detect faces with YuNet; returns an empty list if the model is unavailable."""
    if model_path is None or not Path(model_path).exists():
        return []
    height, width = image_bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(model_path), "", (width, height), min_score, 0.3, 5000)
    detector.setInputSize((width, height))
    _, faces = detector.detect(image_bgr)
    if faces is None:
        return []
    findings: list[Finding] = []
    for face in faces:
        x, y, w, h = (float(value) for value in face[:4])
        findings.append(
            Finding(
                "face",
                page,
                (x, y, x + w, y + h),
                float(face[-1]),
                "yunet",
                "",
            )
        )
    return findings
