# OCR performance

Measured on an Apple Silicon Mac with 8 GB RAM using `tests/fixtures/pii_form.png` and `benchmarks/bench_ocr.py`.

| Backend | Mean | P95 | Recall on fixture |
|---|---:|---:|---:|
| RapidOCR | 448.2 ms | 479.1 ms | 1.000 |
| Indra OCR (optional) | 94.4 ms | 107.6 ms | 1.000 |

Both backends found all seven expected PII kinds on this synthetic form. Indra is optional and requires its own model download.

This is one clean form. It does not measure rotated, blurred, or handwritten documents.
