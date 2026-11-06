"""The adapter with a scripted driver: MOCK evidence for our mapping, none about Oracle itself."""

from __future__ import annotations

import socket
import traceback

import pytest
from conftest import URL
from tarel.connectors.contracts import (
    CatalogRequest,
    ConnectorFailure,
    ProbeRequest,
    SampleRequest,
)
from tarel.connectors.host import load_connector


def connector():
    return load_connector("oracle")


def discover(namespace=None, database=None):
    return connector().discover_catalog(
        CatalogRequest(url=URL, database=database, namespace=namespace)
    )


def by_name(result):
    return {(item.namespace, item.name): item for item in result.objects}


def test_catalog_maps_owners_kinds_types_and_comments(scenario):
    result = discover()

    assert result.catalog == "ORCLCDB"
    assert result.dialect == "oracle"
    objects = by_name(result)
    employees = objects[("HR", "EMPLOYEES")]
    assert employees.kind == "table"
    assert employees.description == "All employees"
    assert employees.primary_key == ("ID",)
    assert [(f.name, f.data_type, f.nullable, f.is_primary_key) for f in employees.fields] == [
        ("ID", "NUMBER(10,0)", False, True),
        ("NAME", "VARCHAR2(50 CHAR)", True, False),
        ("DEPT_ID", "NUMBER(10,0)", True, False),
    ]
    assert employees.fields[0].description == "Primary key"
    assert objects[("HR", "DEPARTMENTS")].fields[0].data_type == "NUMBER"
    assert objects[("SALES", "EMPLOYEES")].fields[0].data_type == "TIMESTAMP(6)"


def test_the_result_passes_the_host_catalog_rules(scenario):
    validate_catalog_result = pytest.importorskip(
        "tarel.connectors.catalog"
    ).validate_catalog_result

    validate_catalog_result(discover())


def test_quoted_names_keep_their_exact_spelling(scenario):
    objects = by_name(discover())

    mixed = objects[("HR", "Mixed Case")]
    assert mixed.kind == "view"
    assert mixed.fields[0].name == "Weird Col"
    assert mixed.fields[0].data_type == "RAW(16)"


def test_same_table_name_in_two_owners_stays_apart(scenario):
    assert {("HR", "EMPLOYEES"), ("SALES", "EMPLOYEES")} <= set(by_name(discover()))


def test_foreign_key_into_something_invisible_is_left_out(scenario):
    relationships = discover().relationships

    assert [item.name for item in relationships] == ["EMP_DEPT"]
    assert relationships[0].from_fields == ("DEPT_ID",)
    assert relationships[0].to_fields == ("ID",)


def test_composite_foreign_key_keeps_its_column_order(scenario):
    columns = [
        ["HR", "A", "TABLE", "X", 1, "NUMBER", 22, 0, None, None, None, "N", None, None],
        ["HR", "A", "TABLE", "Y", 2, "NUMBER", 22, 0, None, None, None, "N", None, None],
        ["HR", "B", "TABLE", "P", 1, "NUMBER", 22, 0, None, None, None, "N", None, None],
        ["HR", "B", "TABLE", "Q", 2, "NUMBER", 22, 0, None, None, None, "N", None, None],
    ]
    keys = [
        ["FK", "HR", "A", "Y", "HR", "B", "Q"],
        ["FK", "HR", "A", "X", "HR", "B", "P"],
    ]
    scenario(columns=columns, foreign_keys=keys, primary_keys=[])

    relationship = discover().relationships[0]

    assert relationship.from_fields == ("Y", "X")
    assert relationship.to_fields == ("Q", "P")


def test_a_namespace_is_bound_as_a_value_in_every_query(scenario):
    result = discover(namespace="HR")

    assert {item.namespace for item in result.objects} == {"HR"}
    executed = [e for e in scenario.log() if e["call"] == "execute" and e["kind"] != "read_only"]
    assert len(executed) == 3
    for entry in executed:
        assert entry["parameters"] == {"owner": "HR"}
        assert ":owner" in entry["sql"]
        assert "HR" not in entry["sql"].replace("WHERE", "")


def test_a_hostile_namespace_stays_a_value(scenario):
    with pytest.raises(ConnectorFailure) as caught:
        discover(namespace="HR' OR '1'='1")
    assert caught.value.code == "namespace_not_found"
    for entry in scenario.log():
        if entry["call"] == "execute" and entry["kind"] != "read_only":
            assert "OR '1'" not in entry["sql"]


def test_only_oracle_maintained_schemas_and_dropped_objects_are_excluded(scenario):
    discover()
    columns = next(e for e in scenario.log() if e.get("kind") == "columns")
    assert "users.oracle_maintained = 'N'" in columns["sql"]
    assert "NOT LIKE 'BIN$%'" in columns["sql"]


def test_it_only_ever_reads(scenario):
    discover()
    connector().probe(ProbeRequest(url=URL))

    statements = [e["sql"].strip().upper() for e in scenario.log() if e["call"] == "execute"]
    for statement in statements:
        assert statement.startswith(("SET TRANSACTION READ ONLY", "SELECT")), statement
    assert statements.count("SET TRANSACTION READ ONLY") == 2


def test_thin_mode_is_never_switched_off(scenario):
    import sys

    discover()

    assert not hasattr(sys.modules["oracledb"], "init_oracle_client")


def test_probe_reports_identity_and_no_edition_it_cannot_know(scenario):
    result = connector().probe(ProbeRequest(url=URL))

    assert result.database_name == "ORCLCDB"
    assert result.server_name == "dbhost"
    assert result.product_version == "19.3.0.0.0"
    assert result.edition is None
    assert result.read_only is True


def test_database_argument_selects_the_service_and_becomes_the_catalog(scenario):
    assert discover(database="OTHER").catalog == "OTHER"


def test_tcps_is_passed_on_only_when_asked_for(scenario):
    load = connector()
    load.probe(ProbeRequest(url=URL))
    load.probe(ProbeRequest(url=f"{URL}?protocol=tcps"))

    protocols = [e["protocol"] for e in scenario.log() if e["call"] == "connect"]
    assert protocols == ["tcp", "tcps"]


@pytest.mark.parametrize(
    ("kind", "code", "expected"),
    [
        ("connect", "ORA-01017", "authentication_failed"),
        ("connect", "ORA-28000", "authentication_failed"),
        ("connect", "DPY-6005", "connection_failed"),
        ("connect", "ORA-12541", "connection_failed"),
        ("connect", "DPY-3010", "unsupported_source"),
        ("columns", "ORA-00942", "insufficient_privileges"),
        ("foreign_keys", "ORA-01031", "insufficient_privileges"),
        ("columns", "ORA-00904", "unsupported_source"),
        ("primary_keys", "ORA-00600", "discovery_failed"),
    ],
)
def test_driver_failures_get_stable_codes_and_never_leak(scenario, kind, code, expected):
    scenario(fail_on={kind: code})

    with pytest.raises(ConnectorFailure) as caught:
        discover()

    assert caught.value.code == expected
    assert code in str(caught.value)
    rendered = "".join(traceback.format_exception(caught.value))
    for secret in ("tiger", "scott", "s3cr3t"):
        assert secret not in rendered


def test_a_failed_constraint_query_fails_the_whole_discovery(scenario):
    """Rights lost on keys must not look like keys removed."""
    scenario(fail_on={"primary_keys": "ORA-01031"})

    with pytest.raises(ConnectorFailure) as caught:
        discover()

    assert caught.value.code == "insufficient_privileges"


@pytest.mark.parametrize(
    "failure",
    [{}, {"columns": "ORA-00942"}, {"read_only": "ORA-01031"}],
)
def test_connection_is_released_on_success_and_failure(scenario, failure):
    scenario(fail_on=failure)

    with pytest.raises(ConnectorFailure) if failure else _nothing():
        discover()

    calls = [e["call"] for e in scenario.log()]
    assert calls.count("connection_close") == 1
    assert calls.count("cursor_close") == 1


def test_connection_is_released_when_interrupted(scenario, monkeypatch):
    import tarel_connector_oracle.connector as module

    def interrupted(*_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "_query", interrupted)

    with pytest.raises(KeyboardInterrupt):
        discover()

    assert [e["call"] for e in scenario.log()].count("connection_close") == 1


def test_nothing_visible_is_an_error_and_not_an_empty_source(scenario):
    scenario(columns=[], primary_keys=[], foreign_keys=[])

    with pytest.raises(ConnectorFailure) as caught:
        discover()
    assert caught.value.code == "no_visible_objects"

    with pytest.raises(ConnectorFailure) as caught:
        discover(namespace="hr")
    assert caught.value.code == "namespace_not_found"
    assert "exact" in str(caught.value)


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("mysql://scott:s3cr3t@h/s", "unsupported_url"),
        ("oracle://h/s", "invalid_url"),
        ("oracle://scott@h/s", "invalid_url"),
        ("oracle://scott:s3cr3t@h", "invalid_url"),
        ("oracle://scott:s3cr3t@h:notaport/s", "invalid_url"),
        ("oracle://scott:s3cr3t@h/s?wallet=/etc/x", "invalid_url"),
        ("oracle://scott:s3cr3t@h/s?protocol=ftp", "invalid_url"),
    ],
)
def test_bad_urls_are_refused_without_repeating_them(scenario, url, code):
    with pytest.raises(ConnectorFailure) as caught:
        connector().probe(ProbeRequest(url=url))

    assert caught.value.code == code
    assert "s3cr3t" not in str(caught.value)
    assert not scenario_called(scenario)


def test_sample_rows_is_refused_because_it_reads_no_rows(scenario):
    with pytest.raises(ConnectorFailure) as caught:
        connector().sample_rows(
            SampleRequest(url=URL, database=None, namespace="HR", object_name="EMPLOYEES")
        )
    assert caught.value.code == "unsupported_capability"


def test_real_driver_against_a_closed_port_reports_a_clean_failure(
    real_driver_available, monkeypatch
):
    """The real driver and real sockets, no database: the only real-driver evidence so far."""
    monkeypatch.delenv("FAKE_ORACLE_SCENARIO", raising=False)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"oracle://scott:s3cr3t@127.0.0.1:{port}/NOPE"

    with pytest.raises(ConnectorFailure) as caught:
        connector().probe(ProbeRequest(url=url))

    assert caught.value.code == "connection_failed"
    assert "DPY-" in str(caught.value)
    assert "s3cr3t" not in "".join(traceback.format_exception(caught.value))


def scenario_called(scenario):
    try:
        return scenario.log()
    except FileNotFoundError:
        return []


class _nothing:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False
