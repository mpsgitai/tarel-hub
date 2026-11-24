import os

import pytest
from tarel.connectors.contracts import CatalogRequest, ConnectorFailure, ProbeRequest
from tarel.connectors.host import load_connector


def _adapter():
    pytest.importorskip("clickhouse_connect")
    pytest.importorskip("tarel_connector_clickhouse")
    return load_connector("clickhouse")


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("http://u:p@localhost/demo", "unsupported_url"),
        ("clickhouse://u:p@localhost", "invalid_url"),
        ("clickhouse://u:p@localhost/demo?compress=0", "invalid_url"),
    ],
)
def test_invalid_targets_fail_before_connection(url, code):
    with pytest.raises(ConnectorFailure) as error:
        _adapter().probe(ProbeRequest(url))
    assert error.value.code == code


def test_refused_connection_hides_target_details():
    with pytest.raises(ConnectorFailure) as error:
        _adapter().probe(ProbeRequest("clickhouse://someone:s3cr3t@127.0.0.1:9/demo"))
    assert error.value.code == "connection_failed"
    assert "s3cr3t" not in str(error.value) and "127.0.0.1" not in str(error.value)


def test_real_fixture_catalog():
    url = os.environ.get("HUB_TEST_CLICKHOUSE_URL")
    if not url:
        pytest.skip("Requires tests/fixture.sql on a disposable server and HUB_TEST_CLICKHOUSE_URL")
    adapter = _adapter()
    assert adapter.probe(ProbeRequest(url)).database_name == "hubtest"
    catalog = adapter.discover_catalog(CatalogRequest(url))
    objects = {item.name: item for item in catalog.objects}
    # payroll is not granted to the reader and must stay invisible.
    assert sorted(objects) == ["order_totals", "orders"]
    orders = objects["orders"]
    assert orders.description == "Synthetic orders"
    # ORDER BY id is a sort key, not a uniqueness guarantee.
    assert orders.primary_key == ()
    assert [(f.name, f.data_type, f.nullable, f.description) for f in orders.fields] == [
        ("id", "UInt32", False, "Order number"),
        ("customer_id", "Nullable(UInt32)", True, None),
        ("amount", "Decimal(12, 2)", False, None),
    ]
    assert objects["order_totals"].kind == "view"
    with pytest.raises(ConnectorFailure) as error:
        adapter.probe(ProbeRequest(url.replace("hubtest-reader@", "wrong-password@")))
    assert error.value.code == "authentication_failed"
