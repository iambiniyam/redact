# Changelog

## 0.2.1 - 2026-10-18

- Fix the Indra downloader: missing constants and fetch helper.
- Limit uploads to 25 MB and PDFs to 100 pages.
- Delete the original upload after redaction.
- Clean original uploads left by older versions on startup.
- Return a readable error for an invalid PDF.
- Add downloader regression tests.

## 0.2.0 - 2026-10-18

- Rebuilt the web interface with drag and drop, paste, OCR selection, a redacted preview, a findings review table, and an audit report download.
- Added automatic dark mode, keyboard support, loading states, error recovery, and mobile layouts.
- Added optional Indra OCR alongside RapidOCR.
- Added an OCR benchmark for speed, confidence, and PII recall.
- Added a visible audit report link and local-only messaging.

## 0.1.0 - 2026-10-18

First public release.

- Initial working version.
- CLI and local web interface.
- Test suite and GitHub Actions workflow.
