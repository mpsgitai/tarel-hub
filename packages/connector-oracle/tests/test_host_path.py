"""The real, unpatched host driving this package through its entry point, with a scripted driver."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from conftest import BASE_SCENARIO, URL
from tarel.connectors.contracts import ConnectorFailure
from tarel.connectors.host import check_connector, load_manifest
from tarel.errors import TarelError
from tarel.sdk import Tarel


@pytest.fixture()
def config(tmp_path, monkeypatch):
    path = tmp_path / "source.toml"
    path.write_text(f'[oracle]\nurl = "{URL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return path


def build(tmp_path, config, namespace=None):
    client = Tarel(tmp_path / "state")
    client.graph.build("hr", connector="oracle", config=config, namespace=namespace)
    return client


def graph_file(tmp_path):
    return tmp_path / "state" / "graphs" / "hr" / "graph.json"


def test_host_finds_it_as_an_ordinary_installed_connector():
    manifest = load_manifest("oracle")
    assert manifest.entrypoint == "tarel_connector_oracle.connector:create_connector"

    check = check_connector("oracle")
    assert check.name == "oracle"
    assert check.permissions == ("read",)
    assert check.capabilities == ("probe", "discover_catalog")


def test_discovery_and_help_load_no_driver():
    code = (
        "import sys;"
        "from tarel.connectors.host import check_connector;"
        "check_connector('oracle');"
        "import tarel_connector_oracle;"
        "print('oracledb' in sys.modules)"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "False"


def test_first_graph_holds_structure_and_no_connection_details(tmp_path, scenario, config):
    client = build(tmp_path, config)

    graph = client.graph.load("hr")
    assert graph.connector == "oracle"
    assert graph.catalog == "ORCLCDB"
    labels = {node.label for node in graph.nodes}
    assert {"HR.EMPLOYEES", "HR.Mixed Case", "SALES.EMPLOYEES"} <= labels
    assert "foreign_key" in {edge.type for edge in graph.edges}
    text = graph_file(tmp_path).read_text(encoding="utf-8")
    for secret in ("s3cr3t", "scott", "db.example.test", "1522"):
        assert secret not in text


def test_unchanged_refresh_writes_nothing_new(tmp_path, scenario, config):
    client = build(tmp_path, config)
    before = graph_file(tmp_path).read_bytes()

    result = client.graph.refresh("hr", config=config)

    assert result.status == "unchanged"
    assert graph_file(tmp_path).read_bytes() == before


def test_refresh_passes_the_catalog_back_as_the_service(tmp_path, scenario, config):
    client = build(tmp_path, config)

    assert client.graph.refresh("hr", config=config).graph.catalog == "ORCLCDB"


def test_refresh_sees_an_added_column(tmp_path, scenario, config):
    client = build(tmp_path, config, namespace="HR")
    columns = [
        *BASE_SCENARIO["columns"],
        [
            "HR",
            "DEPARTMENTS",
            "TABLE",
            "NAME",
            2,
            "VARCHAR2",
            100,
            100,
            "B",
            None,
            None,
            "Y",
            None,
            None,
        ],
    ]
    scenario(columns=columns)

    result = client.graph.refresh("hr", config=config)

    assert result.status == "changed"
    kinds = {change.kind for change in result.report.changes}
    assert "field_added" in kinds


def test_lost_rights_on_a_query_keep_the_graph_and_record_the_failure(tmp_path, scenario, config):
    client = build(tmp_path, config)
    before = graph_file(tmp_path).read_bytes()
    scenario(fail_on={"columns": "ORA-01031"})

    with pytest.raises(ConnectorFailure) as caught:
        client.graph.refresh("hr", config=config)

    assert caught.value.code == "insufficient_privileges"
    assert graph_file(tmp_path).read_bytes() == before
    observation = client.runtime.graph_store().observation("hr")
    assert observation.failure["code"] == "insufficient_privileges"


def test_an_unreachable_source_keeps_the_graph(tmp_path, scenario, config):
    client = build(tmp_path, config)
    before = graph_file(tmp_path).read_bytes()
    scenario(fail_on={"connect": "DPY-6005"})

    with pytest.raises(ConnectorFailure) as caught:
        client.graph.refresh("hr", config=config)

    assert caught.value.code == "connection_failed"
    assert graph_file(tmp_path).read_bytes() == before


def test_known_gap_a_revoked_grant_looks_like_a_deletion(tmp_path, scenario, config):
    """Pins an open host gap, proposal 0002.

    ALL_* views simply stop showing an object once a grant goes. The connector contract has no way
    to say "complete only as far as this account can see", so the host records a removal.
    """
    client = build(tmp_path, config)
    remaining = [row for row in BASE_SCENARIO["columns"] if row[1] != "DEPARTMENTS"]
    scenario(columns=remaining, primary_keys=[["HR", "EMPLOYEES", "ID"]], foreign_keys=[])

    result = client.graph.refresh("hr", config=config)

    assert "object_removed" in {change.kind for change in result.report.changes}


def test_cli_and_sdk_reach_the_same_graph_and_error_codes(tmp_path, scenario, config, capsys):
    from tarel.cli import main

    client = build(tmp_path, config)
    sdk_graph = json.loads(graph_file(tmp_path).read_text(encoding="utf-8"))

    assert main(["graph", "build", "hr", "--connector", "oracle", "--config", str(config)]) == 0
    capsys.readouterr()
    cli_graph = json.loads(
        (tmp_path / ".tarel" / "graphs" / "hr" / "graph.json").read_text("utf-8")
    )
    assert cli_graph == sdk_graph

    scenario(fail_on={"connect": "ORA-01017"})
    assert main(["connector", "probe", "oracle", "--config", str(config)]) == 2
    error = capsys.readouterr().err
    assert "authentication_failed" in error
    with pytest.raises(TarelError) as caught:
        client.graph.refresh("hr", config=config)
    assert caught.value.code == "authentication_failed"
