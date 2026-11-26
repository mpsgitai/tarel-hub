# Implementation Status

Current reference host: `tarel>=0.0.6,<0.1` (`mpsgitai/tarel`).

All eight hub packages are MIT-licensed adapters distributed from this repository (`Private :: Do Not Upload` remains set until PyPI publishing is enabled).

## Verified packages

| Package | Entry point(s) | Verification |
| --- | --- | --- |
| `connector-duckdb` | `tarel.connectors:duckdb` | Real DuckDB 2.0.0 file fixture + contract & wheel checks |
| `connector-postgres` | `tarel.connectors:postgres` | Real PostgreSQL 17.7 / 16.3 servers + column-level `SELECT` privilege unit test |
| `connector-mysql` | `tarel.connectors:mysql` | Real MySQL 8.4 / MariaDB 11.4 container fixtures |
| `connector-clickhouse` | `tarel.connectors:clickhouse` | Real ClickHouse 25.8 container fixture |
| `connector-oracle` | `tarel.connectors:oracle` | Real Oracle 23ai Free container fixture + 48 unit/mock tests |
| `connector-mongodb` | `tarel.connectors:mongodb` | Real MongoDB 8.0 container fixture + contract checks |
| `lineage-sqlglot` | `tarel.lineage_analyzers:sqlglot` | Real SQLGlot 30.19.0 suite (11 tests) + host entry-point E2E |
| `retrieval-llamacpp` | `tarel.embeddings:llamacpp`, `tarel.rerankers:llamacpp` | Plugin contract tests + pinned Qwen3 HTTPS/SHA-256 registry checks |

## Known boundaries (by design)

- **Hub connector auth:** Hub connectors currently accept connection URLs (and libpq defaults for PostgreSQL); they do not yet declare TAREL's `auth = [...]` manifest block (`tarel` built-in SQL Server supports `auth = "integrated"`).
- **MySQL TLS verification:** `connector-mysql` does not yet expose explicit CA-bundle/hostname verification options; use only over trusted networks until TLS options are added.
- **Oracle revoked privileges:** When `SELECT` privilege is revoked from the metadata reader, Oracle omits the object from `ALL_TABLES`/`ALL_VIEWS`. Do not treat absence alone as a confirmed source deletion.
- **Repository & distribution checks:** Run `python tools/catalog.py validate`, `python tools/check_licenses.py`, `python -m pytest contract-tests/`, and `python tools/check_distribution.py <dist-dir>`.
