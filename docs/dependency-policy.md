# Dependency and Distribution Policy

Every package in TAREL Hub ships only small MIT-licensed adapter code. Third-party drivers, parsers, runtimes, and model weights are never bundled or redistributed here.

## Automated checks

| Check | Tool | What it enforces |
| --- | --- | --- |
| Catalog consistency | `tools/catalog.py validate` | Every package under `packages/` is listed; package name, all declared entry points, and non-`tarel` dependencies match `pyproject.toml`. |
| License metadata | `tools/check_licenses.py` | Every dependency in `pyproject.toml` has an audited entry in `licenses.toml` with SPDX identifier and source URL. |
| Archive inspection | `tools/check_distribution.py` | Inspects built `.whl` and `.tar.gz` archives: rejects binaries (ELF/PE/Mach-O/GGUF/SQLite/nested archives), rejects vendored or unexpected top-level packages (strict allowlist), rejects private paths/secrets, requires `LICENSE` + `THIRD_PARTY_NOTICES.md`, and requires tested upper bounds on dependencies. |
| Host contract tests | `pytest contract-tests/` | Verifies entry-point loading, manifest validation, name-collision rejection (`ambiguous_connector`), and repository rules. |

## What these checks do not replace

Automated checks provide review evidence, not legal advice. Maintainers still review upstream driver licenses and security advisories before adding or bumping dependencies.
