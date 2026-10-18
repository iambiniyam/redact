# OCR evaluation

This compares the two OCR backends on the synthetic PII form used by the tests. It measures speed, line confidence, and whether the detector still finds all seven labelled PII types.

## Fixture

`tests/fixtures/pii_form.png` contains:

- name
- email
- phone
- card number
- passport number
- address
- date of birth

The data is fake.

## Method

1. Load the image once to warm the OCR model.
2. Run the backend five times.
3. Measure mean and p95 latency.
4. Run the regex and label detectors on the resulting lines.
5. Check which of the seven expected PII types were found.

Run it with:

```bash
python benchmarks/bench_ocr.py
```

## Results

| Backend | Lines | Mean confidence | Mean latency | P95 latency | PII recall |
|---|---|---|---|---|---|
| RapidOCR | 8 | 0.985 | 1060 ms | 1201 ms | 1.00 |
| Indra OCR | 8 | 0.990 | 248 ms | 457 ms | 1.00 |

Both backends found all seven PII types. Indra was about four times faster and slightly more confident on this image.

## Caveats

- The image is clean, high contrast, and machine generated. Real scans, phone photos, and skewed pages are harder.
- This measures type-level recall, not character-level OCR accuracy.
- Indra model weights use an OpenRAIL-M license. RapidOCR is Apache-2.0.
- Indra is optional. RapidOCR remains the default fallback and works without extra model downloads.

The result is the reason `auto` chooses Indra when its models are installed, and RapidOCR otherwise.
