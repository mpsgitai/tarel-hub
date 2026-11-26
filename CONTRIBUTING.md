# Contributing to TAREL Hub

## Core Rules

1. **Adapter code only:** Never vendor third-party drivers, binaries, or model weights. Declare external libraries as standard Python dependencies with tested upper bounds.
2. **Read-only by default:** Metadata connectors must never modify source databases and must never leak credentials or host details in error messages.
3. **Explicit license audit:** Every package must include `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, and `licenses.toml` matching `pyproject.toml`.
4. **English only:** All code, comments, docs, error messages, and tests are in English.

## Required Local Checks

```bash
ruff check .
python tools/catalog.py validate
python tools/check_licenses.py
pytest contract-tests/
```

For every changed package, also build its wheel/sdist and run `python tools/check_distribution.py <dist-dir>` plus its unit tests under `packages/<name>/tests/`.
