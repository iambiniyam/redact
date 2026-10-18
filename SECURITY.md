# Security

redact handles identity documents and other sensitive files. If you find a way to leak data through the redactor, please report it privately.

Email: biniyam.gashaw@hotmail.com

Please do not attach a real passport, ID card, medical record, or receipt to a public issue. Use a synthetic sample instead.

## Scope

Examples of issues worth reporting:

- text that remains selectable or copyable after redaction
- metadata or annotations that survive the export
- a path traversal or file disclosure in the web interface
- a crash that writes unredacted content to a temporary file

## What is not a security issue

- a missed detection caused by blurry, rotated, or handwritten input
- a face that the detector does not find
- a finding that appears on the wrong part of the page

Those are accuracy bugs. Open a normal issue with a synthetic sample.
