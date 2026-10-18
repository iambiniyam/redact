# Comparison

## Similar tools

- [Microsoft Presidio](https://github.com/microsoft/presidio) is an open-source PII detection and anonymization toolkit. It is the strongest reference for configurable recognizers.
- Adobe Acrobat and hosted redaction products handle polished PDF workflows, but the document goes to a service.

## What redact does differently

- One local command or local page for PDFs and photos, including OCR and face detection.
- The output PDF is rasterized so the original text layer and metadata cannot leak.
- Per-finding review: uncheck a false positive and only the accepted findings are redacted.
- A masked JSON report and a masked HTML audit report are written next to the redacted file.
- No upload, account, or cloud API.

## Tradeoff

Presidio has a much larger recognizer library and can be embedded in a larger data pipeline. redact is narrower and optimized for one document at a time with a human review step.
