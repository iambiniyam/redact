# redact

[![ci](https://github.com/iambiniyam/redact/actions/workflows/ci.yml/badge.svg)](https://github.com/iambiniyam/redact/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Remove personal information from documents before you share them.

Drop in a PDF or a photo. redact finds emails, phone numbers, card numbers, IBANs, SSNs, names, addresses, passport and ID fields, and faces. It blacks them out and leaves an audit report. The file never leaves your machine.

![redact web UI](docs/demo.png)

Status: early MVP. Detection is OCR-based and the output should always be reviewed before it is sent.

## Why

People send passport photos, medical forms, contracts, and receipts over email and chat every day. Many PDF redaction tools upload the original file. Some leave the text underneath the black box, where it can still be copied or searched.

redact keeps the file local. It also flattens PDF pages and clears metadata, so hidden text and annotations do not survive the export.

## What it finds

| Type | Examples | Method |
|---|---|---|
| Email | john.doe@example.com | regex |
| Phone | +1 555 123 4567 | regex and digit count check |
| Card | 4111 1111 1111 1111 | regex and Luhn check |
| IBAN | GB82 WEST 1234 5698 7654 32 | regex and mod-97 check |
| SSN | 123-45-6789 | regex |
| Name, address, date of birth | labeled form fields such as `Name:` and `Address:` | line labels |
| Passport and national ID | labeled fields such as `Passport:` and `ID No:` | line labels |
| Face | portraits and ID photos | YuNet via OpenCV |

## Quickstart

```bash
git clone https://github.com/iambiniyam/redact.git
cd redact
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/download_models.py
redact scan tests/fixtures/pii_form.png
redact apply tests/fixtures/pii_form.png -o form.redacted.png --report report.json
redact serve
```

The face detector is about 230 KB. The OCR models ship with the RapidOCR wheel.

## CLI

```bash
# detect only, no output file
redact scan contract.pdf

# redact and write a machine-readable audit report
redact apply contract.pdf -o contract.safe.pdf --report audit.json

# skip faces, which is faster and does not need the model
redact apply id.png --no-faces
```

Example output:

```
Findings: {'email': 1, 'phone': 1, 'card': 1}
+--------+------+------------------+--------+------------+
| Kind   | Page | Preview          | Source | Confidence |
+--------+------+------------------+--------+------------+
| email  |    1 | j***@example.com | regex  |       1.00 |
| phone  |    1 | ***4567          | regex  |       0.98 |
| card   |    1 | ***1111          | regex  |       0.98 |
+--------+------+------------------+--------+------------+
```

## How it works

```
PDF or image
  |
  v
render at 200 DPI
  |
  v
text layer or RapidOCR
  |
  +--> regex and labeled fields
  |
  +--> YuNet face detection
  |
  v
black rectangles
  |
  v
rasterized PDF or PNG, plus a masked audit JSON
```

- Digital PDFs use the embedded text layer, which gives accurate boxes.
- Scanned PDFs and images go through RapidOCR, which runs on CPU with ONNX.
- Faces use YuNet when `scripts/download_models.py` has been run.
- PDF output is rasterized on purpose. The text layer, annotations, and metadata are removed.

## Privacy

- No telemetry, no API keys, and no network calls at runtime.
- Audit reports store masked previews such as `j***@example.com` and `***1111`, plus a digest. They do not store the original value.
- PDFs are flattened and metadata is cleared.
- The web UI writes to `~/.redact/out`. You can delete that folder at any time.

## Limits

- OCR is not perfect. Rotated, blurred, handwritten, or low-contrast text can be missed.
- Signatures, stamps, and license plates are not detected yet.
- Label-based fields only work when the form uses a label such as `Name:` or `Address:`.
- Faces need the YuNet model. Profile faces and very small faces can be missed.
- Review the redacted file before sharing it. This tool reduces risk. It does not remove all of it.

## Tests

```bash
pytest -q
```

The suite has 7 tests covering detectors, the engine, the PDF pipeline, and faces.

## Roadmap

- signature and stamp detection
- license plate detection
- multilingual NER for names and addresses without labels
- batch mode with a review queue
- side-by-side review with accept or reject for each finding
- optional text-layer-preserving redaction with verified removal
- a public benchmark that measures recall per PII type

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). For security issues, see [SECURITY.md](SECURITY.md).

## Related tools

- [shamba](https://github.com/iambiniyam/shamba): offline plant health scanner for gardeners and farmers.
- [snap2sheet](https://github.com/iambiniyam/snap2sheet): receipt and invoice photos to CSV or Excel.
- [find-local](https://github.com/iambiniyam/find-local): offline semantic search for files, PDFs, and photos.

## License

MIT. The YuNet face model comes from the OpenCV Zoo and has its own license. See [THIRD_PARTY.md](THIRD_PARTY.md).
