"""Command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Paths
from .engine import process
from .ocr import backend_status

app = typer.Typer(add_completion=False, help="Offline PII redaction for PDFs and images.")
console = Console()


def _print_findings(result) -> None:
    if not result.findings:
        console.print("[yellow]No PII detected. Review manually before sharing.[/yellow]")
        return
    table = Table(title=f"Findings · {result.counts}")
    table.add_column("Kind")
    table.add_column("Page", justify="right")
    table.add_column("Preview")
    table.add_column("Source")
    table.add_column("Confidence", justify="right")
    for finding in result.findings:
        table.add_row(
            finding.kind,
            str(finding.page + 1),
            finding.masked(),
            finding.source,
            f"{finding.confidence:.2f}",
        )
    console.print(table)


@app.command()
def scan(
    file: Path = typer.Argument(..., exists=True, readable=True),
    dpi: int = typer.Option(200, help="Rasterization DPI for PDFs."),
    no_faces: bool = typer.Option(False, "--no-faces", help="Skip face detection."),
    ocr: str = typer.Option("auto", "--ocr", help="auto, rapidocr, or indra."),
    json_out: bool = typer.Option(False, "--json", help="Print the report as JSON."),
) -> None:
    """Detect PII without writing a redacted file."""
    model = None if no_faces else Paths.default().face_model
    result = process(file, dry_run=True, dpi=dpi, face_model=model, ocr_backend=ocr)
    if json_out:
        typer.echo(json.dumps(result.report(), indent=2, ensure_ascii=False))
        return
    _print_findings(result)
    for warning in result.warnings:
        console.print(f"[dim]{warning}[/dim]")


@app.command()
def apply(
    file: Path = typer.Argument(..., exists=True, readable=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
    report: Path | None = typer.Option(None, "--report", "-r"),
    dpi: int = typer.Option(200),
    no_faces: bool = typer.Option(False, "--no-faces"),
    ocr: str = typer.Option("auto", "--ocr", help="auto, rapidocr, or indra."),
) -> None:
    """Redact a PDF or image and write an audit report."""
    model = None if no_faces else Paths.default().face_model
    result = process(
        file, output_path=output, report_path=report, dpi=dpi, face_model=model, ocr_backend=ocr
    )
    _print_findings(result)
    if result.output_path:
        console.print(Panel(f"[green]{result.output_path}[/green]", title="Redacted file"))
    if report:
        console.print(f"report: {report}")
    console.print("[dim]Always review the output before sharing it.[/dim]")


@app.command()
def serve(host: str = typer.Option("127.0.0.1"), port: int = typer.Option(8788)) -> None:
    """Start the local drag-and-drop web UI."""
    import uvicorn

    uvicorn.run("redact.server:app", host=host, port=port, log_level="info")


@app.command()
def doctor() -> None:
    """Check OCR, face model, and runtime readiness."""
    import cv2
    import pymupdf as fitz

    paths = Paths.default()
    console.print(f"pymupdf: [bold]{fitz.__version__}[/bold]")
    console.print(f"opencv: [bold]{cv2.__version__}[/bold]")
    console.print(
        f"face model: {paths.face_model} "
        f"{'[green]found[/green]' if paths.face_model.exists() else '[yellow]missing (faces disabled)[/yellow]'}"
    )
    if not paths.face_model.exists():
        console.print("Run: [bold]python scripts/download_models.py[/bold]")
    status = backend_status()
    console.print(f"OCR: [bold]{status['auto']}[/bold] (indra installed: {status['indra']})")
    if not status["indra"]:
        console.print("  optional: python scripts/download_models.py --with-indra")
    console.print("[green]ready[/green]")
