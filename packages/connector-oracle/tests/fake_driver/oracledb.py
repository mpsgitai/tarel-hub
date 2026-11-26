"""A scripted stand-in for python-oracledb. MOCK: it proves our mapping, never Oracle's behaviour.

A scenario is JSON in the file ``FAKE_ORACLE_SCENARIO`` names: rows per query kind, and the codes to
raise. Calls are appended to ``FAKE_ORACLE_LOG``, so tests in another process can see them.
"""

from __future__ import annotations

import json
import os


class _ErrorObject:
    def __init__(self, code: str) -> None:
        self.full_code = code
        self.message = f"{code}: secret-laden driver message for scott/tiger@db"


class Error(Exception):
    pass


def _scenario() -> dict:
    with open(os.environ["FAKE_ORACLE_SCENARIO"], encoding="utf-8") as handle:
        return json.load(handle)


def _log(entry: dict) -> None:
    path = os.environ.get("FAKE_ORACLE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def _kind(sql: str) -> str:
    if "SET TRANSACTION READ ONLY" in sql:
        return "read_only"
    if "all_tab_columns" in sql:
        return "columns"
    if "constraint_type = 'P'" in sql:
        return "primary_keys"
    if "constraint_type = 'R'" in sql:
        return "foreign_keys"
    if "DUAL" in sql:
        return "probe"
    return "other"


class _Cursor:
    arraysize = 100

    def __init__(self, scenario: dict) -> None:
        self.scenario = scenario
        self.rows: list = []

    def execute(self, sql: str, parameters: dict | None = None) -> None:
        kind = _kind(sql)
        _log({"call": "execute", "kind": kind, "sql": sql, "parameters": parameters})
        code = self.scenario.get("fail_on", {}).get(kind)
        if code:
            raise Error(_ErrorObject(code))
        rows = self.scenario.get(kind, [])
        if parameters:
            rows = [row for row in rows if row[1 if kind == "foreign_keys" else 0] == parameters["owner"]]
        self.rows = [tuple(row) for row in rows]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self) -> None:
        _log({"call": "cursor_close"})


class _Connection:
    version = "19.3.0.0.0"
    call_timeout = 0

    def __init__(self, scenario: dict) -> None:
        self.scenario = scenario

    def cursor(self) -> _Cursor:
        return _Cursor(self.scenario)

    def close(self) -> None:
        _log({"call": "connection_close"})


def connect(**kwargs) -> _Connection:
    _log({"call": "connect", "keys": sorted(kwargs), "protocol": kwargs.get("protocol")})
    scenario = _scenario()
    code = scenario.get("fail_on", {}).get("connect")
    if code:
        raise Error(_ErrorObject(code))
    return _Connection(scenario)
