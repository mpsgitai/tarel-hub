# TAREL connector-duckdb

Read-only metadata connector for local DuckDB files. Pass an absolute file path or `duckdb:///absolute/path.duckdb`. Reads tables, views, columns, and primary keys in the selected schema. Use only with trusted local files.

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-duckdb"
tarel connector check duckdb
```

## Configuration

Use section `[duckdb]` with key `url`, or environment variable `TAREL_DUCKDB_URL`. Both `probe` and `discover_catalog` open the database file read-only.
