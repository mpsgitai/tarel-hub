# TAREL Hub

Installable, read-only metadata connectors and optional extensions for [TAREL](https://github.com/mpsgitai/tarel).

Install only the single package you need into your TAREL environment — never the entire hub.

## Available packages

All hub packages are currently **experimental** and installed directly from this repository (PyPI releases will follow once contracts settle):

| Package | Capabilities | Auth & Security Notes | Install |
| --- | --- | --- | --- |
| [connector-duckdb](packages/connector-duckdb/README.md) | `probe`, `discover_catalog` | Local DuckDB file (trusted files only) | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-duckdb"` |
| [connector-postgres](packages/connector-postgres/README.md) | `probe`, `discover_catalog` | Read-only tx, column-level `SELECT` privilege check; URL or libpq (`pgpass`/SSPI/GSSAPI/peer) | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-postgres[binary]"` |
| [connector-mysql](packages/connector-mysql/README.md) | `probe`, `discover_catalog` | MySQL 8 / MariaDB 11; URL credentials; see README for TLS verification limits | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-mysql"` |
| [connector-clickhouse](packages/connector-clickhouse/README.md) | `probe`, `discover_catalog` | Read-only HTTP/HTTPS queries; URL credentials | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-clickhouse"` |
| [connector-oracle](packages/connector-oracle/README.md) | `probe`, `discover_catalog` | Thin mode (`oracledb`); URL credentials; revoked privileges appear as absent objects | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-oracle"` |
| [connector-mongodb](packages/connector-mongodb/README.md) | `probe`, `discover_catalog` | Collection & schema metadata; URL credentials | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-mongodb"` |
| [lineage-sqlglot](packages/lineage-sqlglot/README.md) | `lineage-analysis` | Requires `tarel>=0.0.6`; conservative write-centred static SQL analysis | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/lineage-sqlglot"` |
| [retrieval-llamacpp](packages/retrieval-llamacpp/README.md) | `embeddings`, `reranking` | Requires `tarel>=0.0.6`; CPU Qwen3 via `llama-cpp-python`; pinned HTTPS + SHA-256 model links only | `uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/retrieval-llamacpp"` |

Inspect the full catalog without importing any plugin:

```bash
python tools/catalog.py list
python tools/catalog.py show connector-postgres
```

## Architecture, Licensing & Trust Boundaries

- **Links and dependencies only:** This repository ships only small MIT-licensed adapter code. External drivers (`psycopg`, `oracledb`, `duckdb`, `PyMySQL`, `clickhouse-connect`, `pymongo`, `sqlglot`, `llama-cpp-python`) are declared as standard Python dependencies and installed from PyPI by the user.
- **No bundled binaries or model weights:** Model artifacts (such as Qwen3 GGUF files, Apache-2.0) are never stored or redistributed here; they are referenced via pinned HTTPS URLs + SHA-256 checksums and downloaded only on explicit `tarel model download`.
- **Explicit activation:** Installing a package does not activate it or grant sandbox isolation. `tarel connector list` and `tarel connector check` inspect manifests without executing plugin code.
- **Documentation:** See [docs/dependency-policy.md](docs/dependency-policy.md), [docs/real-source-tests.md](docs/real-source-tests.md), [SECURITY.md](SECURITY.md), and [CONTRIBUTING.md](CONTRIBUTING.md).
