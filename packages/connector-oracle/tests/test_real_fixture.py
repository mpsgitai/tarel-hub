"""Real Oracle evidence: tests/fixture.sql on a disposable server, read as hubtest_reader."""

import os

import pytest
from tarel.connectors.contracts import CatalogRequest, ConnectorFailure, ProbeRequest
from tarel.connectors.host import load_connector


@pytest.fixture()
def real_url(real_driver_available):
    url = os.environ.get("HUB_TEST_ORACLE_URL")
    if not url:
        pytest.skip("Requires tests/fixture.sql and HUB_TEST_ORACLE_URL for hubtest_reader")
    return url


def test_real_fixture_catalog(real_url):
    adapter = load_connector("oracle")
    assert adapter.probe(ProbeRequest(real_url)).read_only
    catalog = adapter.discover_catalog(CatalogRequest(real_url, namespace="HUBTEST"))
    objects = {item.name: item for item in catalog.objects}
    # PAYROLL is not granted to the reader and must stay invisible.
    assert sorted(objects) == ["CUSTOMERS", "MixedCase", "ORDERS", "ORDER_LINES", "ORDER_TOTALS"]
    customers = objects["CUSTOMERS"]
    assert customers.description == "Customer master"
    assert [(f.name, f.data_type, f.description) for f in customers.fields] == [
        ("ID", "NUMBER(10,0)", None),
        ("NAME", "VARCHAR2(80 BYTE)", "Display name"),
    ]
    assert objects["ORDER_LINES"].primary_key == ("LINE_NO", "ORDER_ID")
    assert objects["MixedCase"].fields[0].name == "Quoted Column"
    assert objects["ORDER_TOTALS"].kind == "view"
    assert sorted((r.name, r.to_object) for r in catalog.relationships) == [
        ("ORDERS_CUSTOMER_FK", "CUSTOMERS"),
        ("ORDER_LINES_ORDER_FK", "ORDERS"),
    ]


def test_real_wrong_password_is_an_authentication_failure(real_url):
    wrong = real_url.replace("hubtest-reader@", "wrong-password@")
    with pytest.raises(ConnectorFailure) as caught:
        load_connector("oracle").probe(ProbeRequest(wrong))
    assert caught.value.code == "authentication_failed"
    assert "wrong-password" not in str(caught.value)
