# TAREL connector-postgres

Read-only PostgreSQL metadata connector. Reads tables, views, materialized views, foreign tables, columns, comments, primary keys, and foreign keys from `pg_catalog` inside a read-only transaction with a 30 s statement timeout.

Only tables and individual columns on which the login holds `SELECT` privilege (`has_column_privilege`) are reported; partitions are represented via their parent table. No table rows are read.

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-postgres[binary]"
tarel connector check postgres
```

The `[binary]` extra installs `psycopg-binary` (bundling libpq, OpenSSL, and Kerberos). Without `[binary]`, `psycopg` uses the system `libpq`.

## Configuration & Auth

Use section `[postgres]` with key `url` or environment variable `TAREL_POSTGRES_URL`, e.g. `postgresql://reader@db.example:5432/dwh`. When no password is present in the URL, `libpq` handles authentication (`PGPASSFILE`/`pgpass`, SSPI, GSSAPI, or peer). TAREL's `auth = [...]` manifest block is not yet declared by this adapter.
