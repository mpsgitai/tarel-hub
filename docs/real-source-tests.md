# Real-Source Connector Tests

Each database connector has a reproducible disposable container fixture under `packages/connector-<name>/tests/`. All tests are strictly read-only against a dedicated reader role.

| Connector | Container image | Fixture script | Environment variable | Example local URL |
| --- | --- | --- | --- | --- |
| `postgres` | `postgres:17.7-bookworm` | `tests/fixture.sql` (as `postgres`) | `HUB_TEST_POSTGRES_URL` | `postgresql://hubtest_reader:hubtest-reader@127.0.0.1:55432/postgres` |
| `oracle` | `gvenzl/oracle-free:23-slim-faststart` | `tests/fixture.sql` (as `SYSTEM` on `FREEPDB1`) | `HUB_TEST_ORACLE_URL` | `oracle://hubtest_reader:hubtest-reader@127.0.0.1:51521/FREEPDB1` |
| `mongodb` | `mongo:8.0` | `tests/fixture.py ADMIN_URL` | `HUB_TEST_MONGODB_URL` | `mongodb://hubtest_lister:hubtest-lister@127.0.0.1:57017/hubtest` |
| `mysql` | `mysql:8.4` / `mariadb:11.4` | `tests/fixture.sql` (as `root`) | `HUB_TEST_MYSQL_URL`, `HUB_TEST_MARIADB_URL` | `mysql://hubtest_reader:hubtest-reader@127.0.0.1:53306/hubtest` |
| `clickhouse` | `clickhouse/clickhouse-server:25.8` | `tests/fixture.sql` (as admin, `--multiquery`) | `HUB_TEST_CLICKHOUSE_URL` | `clickhouse://hubtest_reader:hubtest-reader@127.0.0.1:58123/hubtest` |

Bind disposable containers to `127.0.0.1` only, use throwaway passwords that are never committed, and remove containers when finished.

## Running a fixture test

```bash
HUB_TEST_POSTGRES_URL="postgresql://hubtest_reader:hubtest-reader@127.0.0.1:55432/postgres" \
  pytest packages/connector-postgres/tests/
```
