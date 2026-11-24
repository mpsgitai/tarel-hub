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
    relationships = {item.name: item for item in catalog.relationships}
    assert sorted(relationships) == ["order_lines_order_fk", "orders_customer_id_fkey"]
    line_fk = relationships["order_lines_order_fk"]
    assert (line_fk.from_fields, line_fk.to_object, line_fk.to_fields) == (
        ("order_id",),
        "orders",
        ("id",),
    )
    with pytest.raises(ConnectorFailure):
        adapter.discover_catalog(CatalogRequest(url, database="missing_database_for_hubtest"))
