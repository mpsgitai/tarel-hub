# TAREL connector-mysql

Read-only metadata connector for MySQL 8 and MariaDB 11. Reads tables, views, columns, comments, primary keys, and foreign keys from `information_schema` without reading table rows.

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-mysql"
tarel connector check mysql
```

## Configuration, Auth & TLS Limits

Use section `[mysql]` with key `url` or environment variable `TAREL_MYSQL_URL`, e.g. `mysql://reader:PASSWORD@host:3306/db`.

- **Auth:** URL credentials only (TAREL's `auth = [...]` manifest block is not yet declared).
- **TLS:** PyMySQL negotiates TLS when the server offers it, but this adapter does not yet expose explicit CA-bundle or hostname verification options. Use only on trusted networks until strict TLS verification options are added.
