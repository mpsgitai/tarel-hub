# TAREL lineage-sqlglot

Conservative, write-centred static SQL lineage analyzer for TAREL via the `tarel.lineage_analyzers` entry point (requires `tarel>=0.0.6`).

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/lineage-sqlglot"
tarel lineage analyze <lineage> --source <file> --analyzer sqlglot
```

Supported dialects: DuckDB, PostgreSQL, SQLite, and SQL Server (`tsql`).
`sqlglot` is declared as an external PyPI dependency and is never bundled in this package.
