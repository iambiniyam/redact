"""Standalone, masked HTML audit report."""

from __future__ import annotations

import html
from datetime import datetime, timezone

from .engine import ScanResult


def render_report(result: ScanResult) -> str:
    rows = []
    for finding in result.findings:
        rows.append(
            "<tr>"
            f"<td>{html.escape(finding.kind.replace('_', ' '))}</td>"
            f"<td>{finding.page + 1}</td>"
            f"<td>{html.escape(finding.masked())}</td>"
            f"<td>{html.escape(finding.source)}</td>"
            f"<td>{finding.confidence:.0%}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="5">No personal information was detected.</td></tr>')
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in result.warnings)
    counts = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in result.counts.items()) or "none"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>redact report: {html.escape(result.input_path.name)}</title>
<style>
:root{{color-scheme:light dark;--ink:#17211b;--muted:#5d6a61;--line:#ddd7c6;--paper:#f7f5ef}}
@media (prefers-color-scheme:dark){{:root{{--ink:#edf2ee;--muted:#a7b5ac;--line:#2d3a33;--paper:#101613}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,sans-serif}}
main{{width:min(860px,100% - 32px);margin:0 auto;padding:40px 0}}h1{{font-size:1.75rem;margin:0 0 4px}}
.meta{{color:var(--muted);margin:0 0 24px}}table{{width:100%;border-collapse:collapse;margin-top:16px;font-size:.9rem}}
th,td{{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.04em}}
.note{{background:#fff4e5;border:1px solid #e3c08d;border-radius:10px;padding:12px 14px;margin-top:20px}}
ul{{padding-left:20px}}@media print{{body{{background:#fff;color:#111}}main{{width:100%;padding:0}}.note{{border-color:#ccc}}}}
</style></head><body><main>
<h1>Redaction audit</h1>
<p class="meta">{html.escape(result.input_path.name)} · {result.pages} page(s) · {generated}</p>
<p><strong>Findings:</strong> {html.escape(counts)}</p>
<table><thead><tr><th>Type</th><th>Page</th><th>Masked preview</th><th>Source</th><th>Confidence</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<div class="note"><strong>Review the redacted file before sharing it.</strong> This report stores masked previews only. It is not a substitute for a manual check of the output.</div>
{'<h2>Warnings</h2><ul>' + warnings + '</ul>' if warnings else ''}
</main></body></html>"""


def write_report(result: ScanResult, path) -> None:
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_report(result), encoding="utf-8")
