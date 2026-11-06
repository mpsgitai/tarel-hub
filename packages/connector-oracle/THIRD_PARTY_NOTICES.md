# Third-party components

This package contains only its own code. Nothing below is copied into its wheel or sdist. Each
component is installed separately, under its own license, from the index you configure.

| Component | Why | Requirement | License | Evidence |
| --- | --- | --- | --- | --- |
| [python-oracledb](https://github.com/oracle/python-oracledb) | Oracle driver, Thin mode | `oracledb>=26.1,<27` | `UPL-1.0 OR Apache-2.0` | `LICENSE.txt`, `NOTICE.txt` and `THIRD_PARTY_LICENSES.txt` in the `oracledb` 26.1.0 wheel, read on 2026-11-04 |
| [TAREL](https://github.com/mpsgitai/tarel) | Host and connector contract | `tarel>=0.0.3,<0.1` | MIT | `license = "MIT"` in the host's `pyproject.toml` |

`oracledb` itself requires `cryptography` and `typing_extensions`; the resolved set per platform is
in `dependency-inventory.*.json`. Oracle Client libraries are not needed in Thin mode and this
package never loads them. Your use of an Oracle Database is governed by your agreement with Oracle.
