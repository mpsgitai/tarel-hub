import os

import pytest
from tarel.connectors.contracts import CatalogRequest, ConnectorFailure, ProbeRequest
from tarel.connectors.host import load_connector


def _adapter():
    pytest.importorskip("psycopg")
    pytest.importorskip("tarel_connector_postgres")
    return load_connector("postgres")


def test_other_schemes_fail_before_connection():
    with pytest.raises(ConnectorFailure) as error:
        _adapter().discover_catalog(CatalogRequest("mysql://localhost/demo"))
    assert error.value.code == "unsupported_url"


def test_refused_connection_hides_target_details():
    url = "postgresql://someone:s3cr3t@127.0.0.1:9/demo"
    with pytest.raises(ConnectorFailure) as error:
        _adapter().probe(ProbeRequest(url))
    assert error.value.code == "connection_failed"
    assert "s3cr3t" not in str(error.value) and "127.0.0.1" not in str(error.value)


def test_real_fixture_catalog():
    url = os.environ.get("HUB_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires tests/fixture.sql on a disposable server and the hubtest_reader URL")
    adapter = _adapter()
    probe = adapter.probe(ProbeRequest(url))
    assert probe.read_only and probe.product_version
    catalog = adapter.discover_catalog(CatalogRequest(url, namespace="hubtest"))
    objects = {item.name: item for item in catalog.objects}
    # payroll is not granted and events_2026 is a partition: neither is reported.
    assert sorted(objects) == ["customers", "events", "order_lines", "order_totals", "orders"]
    customers = objects["customers"]
    assert customers.description == "Customer master"
    assert [(f.name, f.position, f.description) for f in customers.fields] == [
        ("id", 1, None),
        ("name", 2, "Display name"),
    ]
    assert objects["order_lines"].primary_key == ("line_no", "order_id")
    assert objects["order_lines"].fields[2].data_type == "numeric(12,2)"
    assert objects["order_totals"].kind == "view"
    # The partition's cloned key is dropped with the partition; only the parent's key remains.
    assert sorted((item.from_object, item.name) for item in catalog.relationships) == [
        ("events", "events_customer_id_fkey"),
        ("order_lines", "order_lines_order_fk"),
        ("orders", "orders_customer_id_fkey"),
    ]
    relationships = {item.name: item for item in catalog.relationships}
    line_fk = relationships["order_lines_order_fk"]
    assert (line_fk.from_fields, line_fk.to_object, line_fk.to_fields) == (
        ("order_id",),
        "orders",
        ("id",),
    )
    with pytest.raises(ConnectorFailure):
        adapter.discover_catalog(CatalogRequest(url, database="missing_database_for_hubtest"))


def test_column_level_privileges_hide_ungranted_columns_and_constraints():
    from contextlib import contextmanager
    from unittest.mock import patch

    from tarel_connector_postgres import connector as pg_mod

    assert "has_column_privilege(c.oid, a.attnum, 'SELECT')" in pg_mod._COLUMNS

    class _FakeCursor:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class _FakeConn:
        def execute(self, query, _scope=None):
            if query is pg_mod._OBJECTS:
                return _FakeCursor(
                    [("public", "employees", False, "Staff"), ("public", "depts", False, None)]
                )
            if query is pg_mod._COLUMNS:
                # Role only has SELECT on employees.id (not employees.secret_dept_id) and depts.id
                return _FakeCursor(
                    [
                        ("public", "employees", "id", 1, "integer", False, None),
                        ("public", "depts", "id", 1, "integer", False, None),
                    ]
                )
            if query is pg_mod._CONSTRAINTS:
                return _FakeCursor(
                    [
                        ("p", "employees_pkey", "public", "employees", None, None, ["id"], None),
                        (
                            "f",
                            "employees_secret_fk",
                            "public",
                            "employees",
                            "public",
                            "depts",
                            ["secret_dept_id"],
                            ["id"],
                        ),
                    ]
                )
            return _FakeCursor([])

    @contextmanager
    def _fake_session(_request):
        yield _FakeConn(), "demo"

    adapter = pg_mod.PostgresConnector(manifest=None)  # type: ignore[arg-type]
    with patch.object(pg_mod, "_session", _fake_session):
        result = adapter.discover_catalog(CatalogRequest("postgresql://reader@localhost/demo"))
    employees = next(obj for obj in result.objects if obj.name == "employees")
    assert [f.name for f in employees.fields] == ["id"]
    assert employees.primary_key == ("id",)
    assert result.relationships == ()
