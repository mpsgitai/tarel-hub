import os

import pytest
from tarel.connectors.contracts import CatalogRequest, ConnectorFailure, ProbeRequest
from tarel.connectors.host import load_connector


def _adapter():
    pytest.importorskip("pymysql")
    pytest.importorskip("tarel_connector_mysql")
    return load_connector("mysql")


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("postgresql://u:p@localhost/demo", "unsupported_url"),
        ("mysql://u:p@localhost", "invalid_url"),
        ("mysql://u:p@localhost/demo?ssl=false", "invalid_url"),
    ],
)
def test_invalid_targets_fail_before_connection(url, code):
    with pytest.raises(ConnectorFailure) as error:
        _adapter().probe(ProbeRequest(url))
    assert error.value.code == code


def test_refused_connection_hides_target_details():
    with pytest.raises(ConnectorFailure) as error:
        _adapter().probe(ProbeRequest("mysql://someone:s3cr3t@127.0.0.1:9/demo"))
    assert error.value.code == "connection_failed"
    assert "s3cr3t" not in str(error.value) and "127.0.0.1" not in str(error.value)


@pytest.mark.parametrize("variable", ["HUB_TEST_MYSQL_URL", "HUB_TEST_MARIADB_URL"])
def test_real_fixture_catalog(variable):
    url = os.environ.get(variable)
    if not url:
        pytest.skip(f"Requires tests/fixture.sql on a disposable server and {variable}")
    adapter = _adapter()
    probe = adapter.probe(ProbeRequest(url))
    assert probe.read_only and probe.database_name == "hubtest"
    assert probe.edition == ("MariaDB" if "MARIADB" in variable else "MySQL")
    catalog = adapter.discover_catalog(CatalogRequest(url))
    objects = {item.name: item for item in catalog.objects}
    # payroll is not granted to the reader and must stay invisible.
    assert sorted(objects) == ["customers", "order_lines", "order_totals", "orders"]
    customers = objects["customers"]
    assert customers.description == "Customer master"
    assert [(f.name, f.data_type, f.nullable, f.description) for f in customers.fields] == [
        ("id", "int(11)" if "MARIADB" in variable else "int", False, None),
        ("name", "varchar(80)", False, "Display name"),
    ]
    assert objects["order_lines"].primary_key == ("line_no", "order_id")
    assert objects["order_totals"].kind == "view"
    assert sorted((r.name, r.from_fields, r.to_object) for r in catalog.relationships) == [
        ("order_lines_order_fk", ("order_id",), "orders"),
        ("orders_customer_fk", ("customer_id",), "customers"),
    ]
    with pytest.raises(ConnectorFailure) as error:
        adapter.probe(ProbeRequest(url.replace("hubtest-reader@", "wrong-password@")))
    assert error.value.code == "authentication_failed"
