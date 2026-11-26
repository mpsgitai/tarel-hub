# TAREL connector-oracle

Read-only Oracle metadata connector using `oracledb` in pure-Python Thin mode (no Oracle Instant Client required). Reads accessible tables, views, columns, comments, primary keys, and foreign keys from `ALL_*` dictionary views.

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-oracle"
tarel connector check oracle
```

## Configuration, Auth & Visibility Limits

Use section `[oracle]` with key `url` or environment variable `TAREL_ORACLE_URL`, e.g. `oracle://reader:PASSWORD@host:1521/FREEPDB1`.

- **Auth:** URL credentials only (TAREL's `auth = [...]` manifest block is not yet declared).
- **Visibility:** Oracle's `ALL_*` views omit objects when `SELECT` privilege is revoked from the metadata reader. Do not treat an omitted object as a confirmed deletion in the source database.
