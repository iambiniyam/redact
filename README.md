# redact

**Share the document, not your data.**

Drop a PDF or a photo. `redact` finds emails, phone numbers, card numbers, IBANs, SSNs, names, addresses, passport/ID fields, and faces — then blacks them out. Everything runs on your machine; nothing is uploaded.

> Status: early MVP. OCR-based detection, reviewed output. Always inspect the result before sending.

![redact web UI](docs/demo.png)

## Why

Every day people email photos of passports, medical forms, contracts, and receipts to strangers. Cloud "redaction" tools upload the original somewhere, and PDFs routinely leak hidden text, annotations, and metadata underneath the black boxes.

`redact` is the opposite:
- **Local by design** — no network calls after setup.
- **Report-safe** — the audit report stores masked previews, never the raw PII.
- **Rasterized output** — PDF pages are flattened and metadata stripped, so hidden text cannot survive.
- **Simple** — drag, drop, review, download.

## What it finds

| Type | Examples | Method |
|---|---|---|
| Email | `john.doe@example.com` | regex |
| Phone | `+1 555 123 4567` | regex + digit-count check |
| Card | `4111 1111 1111 1111` | regex + Luhn |
| IBAN | `GB82 WEST 1234 5698 7654 32` | regex + mod-97 |
| SSN | `123-45-6789` | regex |
| Name / address / DOB | labeled form fields (`Name:`, `Address:`, `DOB:`) | line labels |
| Passport / national ID | labeled fields (`Passport:`, `ID No:`) | line labels |
| Face | portraits and ID photos | YuNet (OpenCV) |

## Quickstart

```bash
git clone https://github.com/iambiniyam/redact.git
cd redact
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/download_models.py        # ~230 KB face detector; OCR models ship with the wheel
redact scan tests/fixtures/pii_form.png
redact apply tests/fixtures/pii_form.png -o form.redacted.png --report report.json
redact serve                              # http://127.0.0.1:8788
```

## CLI

```bash
# detect only, no output file
redact scan contract.pdf

# redact and write a machine-readable audit report
redact apply contract.pdf -o contract.safe.pdf --report audit.json

# skip faces (faster, no model needed)
redact apply id.png --no-faces
```

Example output:

```
                    Findings · {'email': 1, 'phone': 1, 'card': 1}
┏━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┓
┃ Kind   ┃ Page ┃ Preview          ┃ Source ┃ Confidence ┃
┡━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━┩
│ email  │    1 │ j***@example.com │ regex  │       1.00 │
│ phone  │    1 │ ***4567          │ regex  │       0.98 │
│ card   │    1 │ ***1111          │ regex  │       0.98 │
└────────┴──────┴──────────────────┴────────┴────────────┘
```

## How it works

```
PDF/image ─► render @200 DPI ─► text layer or RapidOCR ─► regex + labeled fields
                                                   │
                                                   └─► YuNet faces
                                                         │
                              black rectangles ◄─────────┘
                                     │
                    rasterized PDF / PNG + masked audit JSON
```

- **Digital PDFs** use the embedded text layer for accurate boxes.
- **Scanned PDFs and images** go through RapidOCR (ONNX, CPU, offline).
- **Faces** use YuNet if `scripts/download_models.py` has been run.
- **PDF output is rasterized** deliberately: no text layer, no annotations, no metadata.

## Privacy design

- No telemetry, no API keys, no network calls at runtime.
- Audit reports contain masked previews (`j***@example.com`, `***1111`) and a digest, not the raw value.
- PDFs are flattened and metadata cleared.
- Output files stay wherever you put them; the web UI writes to `~/.redact/out`.

## Limitations

- **OCR is not perfect.** Rotated, blurred, handwritten, or low-contrast text may be missed.
- **Signatures, stamps, and license plates are not detected yet.**
- **Label-based fields** only work when the form says `Name:`, `Address:`, etc.
- **Faces** need the YuNet model; profile faces and very small faces may be missed.
- **Always review the redacted file** before sharing. This tool reduces risk; it does not eliminate it.

## Roadmap

- [ ] Signature and stamp detection
- [ ] License-plate detection
- [ ] Multilingual NER (names/addresses without labels)
- [ ] Batch mode with a review queue
- [ ] Side-by-side review UI with accept/reject per finding
- [ ] Optional text-layer-preserving PDF redaction with verified removal
- [ ] Benchmark: recall per PII type on a public synthetic corpus

## Tests

```bash
pytest -q     # detectors, engine, PDF pipeline, faces
```

## License

MIT. The YuNet face model is distributed by the OpenCV Zoo under its own license; see [THIRD_PARTY.md](THIRD_PARTY.md).
