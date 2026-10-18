from pathlib import Path

import pytest

from redact.config import Paths
from redact.detectors import (
    TextLine,
    detect_faces,
    detect_lines,
    iban_valid,
    luhn,
)


def test_luhn():
    assert luhn("4111 1111 1111 1111")
    assert not luhn("4111 1111 1111 1112")


def test_iban():
    assert iban_valid("GB82 WEST 1234 5698 7654 32")
    assert not iban_valid("GB82 WEST 1234 5698 7654 31")


def test_detect_lines():
    lines = [
        TextLine("Email: john.doe@example.com", (10, 10, 300, 40)),
        TextLine("Phone: +1 555 123 4567", (10, 50, 300, 80)),
        TextLine("Card: 4111 1111 1111 1111", (10, 90, 300, 120)),
        TextLine("Name: John Doe", (10, 130, 300, 160)),
        TextLine("Address: 42 Main Street", (10, 170, 300, 200)),
    ]
    found = detect_lines(lines)
    kinds = {finding.kind for finding in found}
    assert {"email", "phone", "card", "name", "address"} <= kinds


def test_faces():
    model = Paths.default().face_model
    face = Path(__file__).parent / "fixtures" / "face.jpg"
    if not model.exists() or not face.exists():
        pytest.skip("face model or fixture missing")
    import cv2

    found = detect_faces(cv2.imread(str(face)), model)
    assert len(found) >= 1
