import json

import cv2
import pytest
from PIL import Image, ImageDraw, ImageFont

from redact.engine import process


@pytest.fixture(scope="module")
def pii_image(tmp_path_factory):
    path = tmp_path_factory.mktemp("doc") / "form.png"
    image = Image.new("RGB", (1100, 760), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=30)
    y = 50
    for line in (
        "PATIENT INTAKE FORM",
        "Name: John Doe",
        "Email: john.doe@example.com",
        "Phone: +1 555 123 4567",
        "Card: 4111 1111 1111 1111",
        "Address: 42 Main Street, Springfield",
    ):
        draw.text((60, y), line, fill="black", font=font)
        y += 90
    image.save(path)
    return path


def test_image_redaction(pii_image, tmp_path):
    output = tmp_path / "redacted.png"
    report = tmp_path / "report.json"
    result = process(pii_image, output, report, face_model=None)

    assert output.exists()
    assert result.counts.get("email", 0) >= 1
    assert result.counts.get("card", 0) >= 1
    assert result.counts.get("phone", 0) >= 1
    assert result.counts.get("name", 0) >= 1

    payload = json.loads(report.read_text())
    assert "john.doe@example.com" not in json.dumps(payload)

    redacted = cv2.imread(str(output))
    assert (redacted == 0).all(axis=2).sum() > 2000


def test_dry_run_does_not_write(pii_image, tmp_path):
    output = tmp_path / "should-not-exist.png"
    result = process(pii_image, output, dry_run=True, face_model=None)
    assert not output.exists()
    assert result.output_path is None


def test_pdf_redaction(tmp_path):
    import pymupdf as fitz

    source = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Email: john.doe@example.com", fontsize=14)
    page.insert_text((72, 130), "Card: 4111 1111 1111 1111", fontsize=14)
    doc.save(source)
    doc.close()

    output = tmp_path / "doc.redacted.pdf"
    result = process(source, output, face_model=None)
    assert output.exists()
    assert result.pages == 1
    assert result.counts.get("email", 0) >= 1
    assert any("rasterized" in warning for warning in result.warnings)
