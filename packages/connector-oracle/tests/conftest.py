"""Scripted driver for every test here except those that ask for the real one."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

FAKE_DRIVER = Path(__file__).parent / "fake_driver"

COLUMN = (
    "HR",
    "EMPLOYEES",
    "TABLE",
    "ID",
    1,
    "NUMBER",
    22,
    0,
    None,
    10,
    0,
    "N",
    "All employees",
    "Primary key",
)
BASE_SCENARIO = {
    "probe": [["dbhost", "ORCLCDB"]],
    "columns": [
        list(COLUMN),
        [
            "HR",
            "EMPLOYEES",
            "TABLE",
            "NAME",
            2,
            "VARCHAR2",
            200,
            50,
            "C",
            None,
            None,
            "Y",
            "All employees",
            None,
        ],
        [
            "HR",
            "EMPLOYEES",
            "TABLE",
            "DEPT_ID",
            3,
            "NUMBER",
            22,
            0,
            None,
            10,
            0,
            "Y",
            "All employees",
            None,
        ],
        ["HR", "DEPARTMENTS", "TABLE", "ID", 1, "NUMBER", 22, 0, None, None, None, "N", None, None],
        [
            "HR",
            "Mixed Case",
            "VIEW",
            "Weird Col",
            1,
            "RAW",
            16,
            0,
            None,
            None,
            None,
            "Y",
            None,
            None,
        ],
        [
            "SALES",
            "EMPLOYEES",
            "TABLE",
            "ID",
            1,
            "TIMESTAMP(6)",
            11,
            0,
            None,
            None,
            6,
            "N",
            None,
            None,
        ],
    ],
    "primary_keys": [["HR", "EMPLOYEES", "ID"], ["HR", "DEPARTMENTS", "ID"]],
    "foreign_keys": [
        ["EMP_DEPT", "HR", "EMPLOYEES", "DEPT_ID", "HR", "DEPARTMENTS", "ID"],
        ["EMP_HIDDEN", "HR", "EMPLOYEES", "ID", "SECRET", "INVISIBLE", "ID"],
    ],
}
URL = "oracle://scott:s3cr3t%2Fpw@db.example.test:1522/ORCLCDB"


@pytest.fixture()
def scenario(tmp_path, monkeypatch):
    """Write a scenario, and resolve ``oracledb`` to the fake for this test only."""
    monkeypatch.syspath_prepend(str(FAKE_DRIVER))
    monkeypatch.delitem(sys.modules, "oracledb", raising=False)
    log = tmp_path / "driver.log"
    path = tmp_path / "scenario.json"
    monkeypatch.setenv("FAKE_ORACLE_SCENARIO", str(path))
    monkeypatch.setenv("FAKE_ORACLE_LOG", str(log))

    def write(**changes):
        path.write_text(json.dumps({**BASE_SCENARIO, **changes}), encoding="utf-8")

    write()
    write.log = lambda: [json.loads(line) for line in log.read_text().splitlines()]
    yield write
    sys.modules.pop("oracledb", None)


@pytest.fixture()
def real_driver_available():
    if importlib.util.find_spec("oracledb") is None:
        pytest.skip("oracledb is not installed.")
