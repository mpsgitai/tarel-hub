import os

import pytest
from tarel.connectors.contracts import CatalogRequest, ConnectorFailure
from tarel.connectors.host import load_connector


@pytest.mark.parametrize(
    "url",
    [
        "mongodb://localhost/demo?tlsAllowInvalidCertificates=true",
        "mongodb://localhost/demo?tlsCertificateKeyFile=local.pem",
        "mongodb+srv://example.test/demo",
    ],
)
def test_unsafe_options_fail_before_connection(url):
    pytest.importorskip("pymongo")
    pytest.importorskip("tarel_connector_mongodb")
    with pytest.raises(ConnectorFailure) as error:
        load_connector("mongodb").discover_catalog(CatalogRequest(url))
    assert error.value.code == "invalid_target"


def test_real_synthetic_catalog():
    url = os.environ.get("HUB_TEST_MONGODB_URL")
    if not url:
        pytest.skip("Requires isolated hubtest fixture with orders and orderView")
    catalog = load_connector("mongodb").discover_catalog(CatalogRequest(url, "hubtest"))
    assert [(obj.name, obj.kind, obj.fields) for obj in catalog.objects] == [
        ("orderView", "view", ()),
        ("orders", "table", ()),
    ]
