# tarel-connector-oracle

Reads Oracle table, view, column, primary-key and foreign-key metadata into a TAREL graph. It reads
metadata only, never rows, and needs no Oracle Client.

**Status: never run against a real Oracle Database.** Everything below has been tested with the real
TAREL host and a scripted driver, plus the real driver against a closed port. See
`IMPLEMENTATION_STATUS.md` in the repository root. This package is not published.

## Install

Build the wheel, then install it with the host you use. This brings `oracledb`, nothing else from
this repository, and no other database driver.

```bash
uv build packages/connector-oracle --out-dir dist
uv pip install dist/tarel_connector_oracle-0.0.1-py3-none-any.whl
tarel connector check oracle
```

## Configure

Keep the connection outside the repository. The environment variable wins over the file.

```bash
export TAREL_ORACLE_URL='oracle://USER:PASSWORD@HOST:1521/SERVICE'
```

```toml
[oracle]
url = "oracle://USER:PASSWORD@HOST:1521/SERVICE"
```

Add `?protocol=tcps` for TLS. Percent-encode special characters in the password. Wallets and other
driver options are not supported yet.

## Use

```bash
tarel connector probe oracle --config source.toml
tarel graph build hr --connector oracle --config source.toml --namespace HR
tarel graph refresh hr --config source.toml
```

```python
from tarel.sdk import Tarel

client = Tarel(".tarel")
client.graph.build("hr", connector="oracle", config="source.toml", namespace="HR")
```

## What it needs and what it cannot see

The account needs to connect and read the `ALL_*` catalog views. Prefer a dedicated read-only
account. Oracle Database 12.1 or later is required.

These views show only what the account may access. A namespace is an exact owner name, including
case. Without one, every owner the account can see is read, except Oracle-maintained ones.

| Situation | Result |
| --- | --- |
| Wrong password, locked account | `authentication_failed` |
| Host or listener unreachable | `connection_failed`; the graph stays as it was |
| A catalog view is denied | `insufficient_privileges`; the graph stays as it was |
| Nothing visible at all | `no_visible_objects` or `namespace_not_found` |
| A grant on one object was revoked | **Looks like a deletion**: TAREL cannot tell them apart yet |
| Foreign key into an object it cannot see | Left out |

The fifth row is a real limit: a refresh after a revoked grant records the object as removed, and a
later metadata sync would pass that on. Keep this account's grants stable until the host can express
"complete only as far as this account sees", which is proposed in
`docs/host-proposals/0002-observation-completeness.md`.

Disabled constraints are not reported. Invalid views without columns do not appear.
