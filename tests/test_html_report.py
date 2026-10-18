from pathlib import Path

from redact.engine import ScanResult
from redact.findings import Finding
from redact.html_report import render_report, write_report


def make_result() -> ScanResult:
    return ScanResult(
        input_path=Path("form.pdf"),
        output_path=None,
        pages=2,
        findings=[
            Finding("email", 0, (0, 0, 10, 10), 0.9, "regex", "jane@example.com"),
            Finding("face", 1, (0, 0, 10, 10), 0.8, "yunet", ""),
        ],
        warnings=["PDF output is rasterized."],
    )


def test_report_is_masked_and_standalone():
    page = render_report(make_result())
    assert "<!doctype html>" in page
    assert "j***@example.com" in page
    assert "jane@example.com" not in page
    assert "form.pdf" in page
    assert "2 page(s)" in page


def test_report_writes_file(tmp_path):
    target = tmp_path / "report.html"
    write_report(make_result(), target)
    assert target.exists()
    assert "Redaction audit" in target.read_text()
