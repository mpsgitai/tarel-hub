"""How the real, unpatched host treats plugins, using throwaway installed distributions.

Each case runs in its own process with a temporary directory on ``sys.path``, which
``importlib.metadata`` treats like any installed package. Nothing in the host is replaced.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_MANIFEST = """[connector]
contract_version = {contract}
name = "{name}"
version = "0.0.1"
source_type = "{name}"
entrypoint = "{module}.connector:create_connector"
extra = "{name}"
capabilities = ["probe", "discover_catalog"]
dependencies = {dependencies}
permissions = [{permission}]
"""
_CONNECTOR = """
class Plain:
    def __init__(self, manifest):
        self.manifest = manifest

def create_connector(manifest):
    return Plain(manifest)
"""
_ATTEMPT = """
import json, sys
from tarel.connectors.host import check_connector, load_connector
from tarel.errors import TarelError
try:
    connector = load_connector(sys.argv[1])
    print(json.dumps({"loaded": type(connector).__module__}))
except TarelError as exc:
    print(json.dumps({"code": exc.code}))
"""


def _install(
    site: Path,
    *,
    name: str,
    module: str,
    contract: int = 1,
    permission: str = '"read"',
    dependencies: str = "[]",
    entry_value: str | None = None,
) -> None:
    package = site / module
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "connector.py").write_text(_CONNECTOR, encoding="utf-8")
    (package / "manifest.toml").write_text(
        _MANIFEST.format(
            contract=contract,
            name=name,
            module=module,
            permission=permission,
            dependencies=dependencies,
        ),
        encoding="utf-8",
    )
    info = site / f"{module}-0.0.1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {module}\nVersion: 0.0.1\n",
        encoding="utf-8",
    )
    value = entry_value or f"{module}.connector:create_connector"
    (info / "entry_points.txt").write_text(
        f"[tarel.connectors]\n{name} = {value}\n",
        encoding="utf-8",
    )


def _attempt(site: Path, name: str) -> dict[str, str]:
    environment = {**os.environ, "PYTHONPATH": str(site)}
    done = subprocess.run(
        [sys.executable, "-c", _ATTEMPT, name],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    return json.loads(done.stdout)


def test_an_installed_entry_point_loads(tmp_path):
    _install(tmp_path, name="plain", module="plain_plugin")
    assert _attempt(tmp_path, "plain") == {"loaded": "plain_plugin.connector"}


def test_two_plugins_with_one_name_are_refused_as_ambiguous(tmp_path):
    _install(tmp_path, name="twin", module="twin_one")
    _install(tmp_path, name="twin", module="twin_two")
    assert _attempt(tmp_path, "twin") == {"code": "ambiguous_connector"}


def test_an_unknown_contract_version_is_refused(tmp_path):
    _install(tmp_path, name="future", module="future_plugin", contract=2)
    assert _attempt(tmp_path, "future") == {"code": "unsupported_contract"}


def test_a_plugin_asking_for_write_permission_is_refused(tmp_path):
    _install(tmp_path, name="writer", module="writer_plugin", permission='"read", "write"')
    assert _attempt(tmp_path, "writer") == {"code": "unsafe_manifest"}


def test_a_manifest_disagreeing_with_its_entry_point_is_refused(tmp_path):
    _install(
        tmp_path,
        name="other",
        module="other_plugin",
        entry_value="other_plugin.connector:elsewhere",
    )
    assert _attempt(tmp_path, "other") == {"code": "invalid_manifest"}


def test_a_missing_driver_is_a_clear_failure(tmp_path):
    _install(tmp_path, name="needy", module="needy_plugin", dependencies='["no_such_driver_x"]')
    assert _attempt(tmp_path, "needy") == {"code": "missing_dependency"}


def test_nothing_installed_is_a_clear_failure(tmp_path):
    assert _attempt(tmp_path, "nothing_here") == {"code": "unknown_connector"}


def test_a_plugin_named_like_a_builtin_is_rejected_as_ambiguous(tmp_path):
    """Host rejects any external plugin whose name collides with a built-in connector."""
    _install(tmp_path, name="sqlserver", module="shadow_plugin")

    assert _attempt(tmp_path, "sqlserver") == {"code": "ambiguous_connector"}
