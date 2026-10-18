# Contributing

Thanks for taking a look. Small, focused pull requests are easiest to review.

## Development setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/download_models.py
pytest -q
```

## Before opening a pull request

- Run the test suite.
- Add a test for any detection or output change.
- Update the README if a command, flag, or output changes.

## Test documents

Use synthetic documents in tests. Do not commit real passports, ID cards, medical records, or receipts. The fixture in `tests/fixtures/pii_form.png` is generated and contains fake data.

## Security issues

Do not open a public issue for a bug that could leak data. See [SECURITY.md](SECURITY.md).
