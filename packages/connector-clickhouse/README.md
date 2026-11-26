# TAREL connector-clickhouse

Read-only ClickHouse metadata connector using `clickhouse-connect`. Reads databases, tables, views, columns, comments, and sorting/primary keys from `system.tables` and `system.columns` without reading table rows.

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-clickhouse"
tarel connector check clickhouse
```

## Configuration & Auth

Use section `[clickhouse]` with key `url` or environment variable `TAREL_CLICKHOUSE_URL`, e.g. `clickhouse://reader:PASSWORD@host:8123/db` (or `clickhouses://` for HTTPS). URL credentials only.
