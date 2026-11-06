from pathlib import Path

import pytest
from tarel.connectors.contracts import CatalogRequest, ConnectorFailure
from tarel.connectors.host import load_connector


def test_scoped_metadata_and_file_preservation(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    pytest.importorskip("tarel_connector_duckdb")
    adapter = load_connector("duckdb")
    source = tmp_path / "demo.duckdb"
    with duckdb.connect(str(source)) as conn:
        conn.execute("CREATE SCHEMA sales")
        conn.execute("CREATE TABLE sales.orders(a INT, b INT, PRIMARY KEY (b,a))")
        conn.execute("CREATE TABLE hidden(i INT)")
        conn.execute("CREATE VIEW sales.v AS SELECT a FROM sales.orders")
    before = source.read_bytes()
    result = adapter.discover_catalog(
        CatalogRequest(source.as_uri().replace("file:", "duckdb:"), "demo", "sales")
    )
    table, view = result.objects
    assert (table.name, table.primary_key, view.kind) == ("orders", ("b", "a"), "view")
    assert [f.name for f in table.fields] == ["a", "b"]
    with pytest.raises(ConnectorFailure, match="catalog differs"):
        adapter.discover_catalog(CatalogRequest(str(source), "elsewhere"))
    assert source.read_bytes() == before
    missing = Path(tmp_path, "missing.duckdb")
    with pytest.raises(ConnectorFailure):
        adapter.discover_catalog(CatalogRequest(str(missing)))
    assert not missing.exists()
