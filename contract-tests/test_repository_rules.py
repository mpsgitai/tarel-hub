"""The distribution, license and catalog checks must really catch what they claim to catch."""

from __future__ import annotations

import importlib.util
import io
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


distribution = _load("check_distribution")
licenses = _load("check_licenses")
catalog = _load("catalog")

METADATA = """Metadata-Version: 2.4
Name: tarel-x
Version: 0.0.1
Classifier: Private :: Do Not Upload
Requires-Dist: tarel>=0.0.3,<0.1
"""


def _wheel(path: Path, **overrides: bytes | None) -> Path:
    members: dict[str, bytes | None] = {
        "tarel_x/__init__.py": b'"""Fine."""\n',
        "tarel_x-0.0.1.dist-info/METADATA": METADATA.encode(),
        "tarel_x-0.0.1.dist-info/WHEEL": b"Wheel-Version: 1.0\n",
        "tarel_x-0.0.1.dist-info/RECORD": b"",
        "tarel_x-0.0.1.dist-info/licenses/LICENSE-PENDING.md": b"Pending\n",
        "tarel_x-0.0.1.dist-info/licenses/THIRD_PARTY_NOTICES.md": b"None\n",
    }
    for key, value in overrides.items():
        members[key.replace("__", "/")] = value
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            if data is not None:
                archive.writestr(name, data)
    return path


def _problems(tmp_path: Path, **overrides: bytes | None) -> str:
    return "\n".join(distribution.check_archive(_wheel(tmp_path / "x.whl", **overrides)))


def test_a_clean_wheel_passes(tmp_path):
    assert _problems(tmp_path) == ""


@pytest.mark.parametrize(
    ("name", "data", "expected"),
    [
        ("tarel_x/driver.so", b"\x7fELF....", "ELF binary"),
        ("tarel_x/driver.txt", b"\x7fELF renamed", "ELF binary"),
        ("tarel_x/model.gguf", b"GGUF....", "GGUF model"),
        ("tarel_x/weights.txt", b"GGUF renamed", "GGUF model"),
        ("tarel_x/data.json", b"SQLite format 3\0", "SQLite"),
        ("tarel_x/bundle.txt", b"PK\x03\x04", "nested archive"),
        ("tarel_x/blob.txt", b"abc\0def", "binary data"),
        ("tarel_x/setup.sh", b"echo hi\n", "allowlist"),
        ("tarel_x/app.js", b"var a;\n", "allowlist"),
        ("AGENTS.md", b"rules\n", "private project file"),
        ("tarel_x/_vendor/x.py", b"a = 1\n", "vendored"),
        ("sqlglot/__init__.py", b"a = 1\n", "copy of the package sqlglot"),
        ("oracledb/__init__.py", b"a = 1\n", "copy of the package oracledb"),
        ("tarel_x/tests/test_x.py", b"a = 1\n", "tests do not belong"),
    ],
)
def test_foreign_or_private_content_is_caught(tmp_path, name, data, expected):
    assert expected in _problems(tmp_path, **{name.replace("/", "__"): data})


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----\n", "private key"),
        (b"AKIA" + b"ABCDEFGHIJKLMNOP", "AWS access key"),
        (b"url = 'mssql://sa:Winter" + b"2026!@db.corp.example/x'", "URL with password"),
        (b"path = '/ho" + b"me/someone/x'", "private local path"),
    ],
)
def test_secrets_and_private_paths_are_caught(tmp_path, text, expected):
    assert expected in _problems(tmp_path, tarel_x__conf_py=None, **{"tarel_x__conf.py": text})


def test_made_up_passwords_in_documentation_are_allowed(tmp_path):
    text = b"oracle://USER:PASSWORD@HOST:1521/SERVICE"
    assert _problems(tmp_path, **{"tarel_x__doc.md": text}) == ""


def test_a_missing_notice_is_caught(tmp_path):
    key = "tarel_x-0.0.1.dist-info__licenses__THIRD_PARTY_NOTICES.md"
    assert "THIRD_PARTY_NOTICES" in _problems(tmp_path, **{key: None})


def test_a_dependency_without_an_upper_bound_is_caught(tmp_path):
    metadata = METADATA + "Requires-Dist: requests>=2\n"
    key = "tarel_x-0.0.1.dist-info__METADATA"
    assert "upper bound" in _problems(tmp_path, **{key: metadata.encode()})


def test_an_undecided_license_without_upload_protection_is_caught(tmp_path):
    metadata = METADATA.replace("Classifier: Private :: Do Not Upload\n", "")
    key = "tarel_x-0.0.1.dist-info__METADATA"
    assert "Do Not Upload" in _problems(tmp_path, **{key: metadata.encode()})


def test_an_entry_point_without_a_matching_manifest_is_caught(tmp_path):
    entry = b"[tarel.connectors]\nx = tarel_x.connector:create_connector\n"
    key = "tarel_x-0.0.1.dist-info__entry_points.txt"
    assert "manifest" in _problems(tmp_path, **{key: entry})


def test_an_sdist_symlink_and_missing_files_are_caught(tmp_path):
    path = tmp_path / "x-0.0.1.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("x-0.0.1/link.py")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        archive.addfile(info)
        data = b"a = 1\n"
        plain = tarfile.TarInfo("x-0.0.1/a.py")
        plain.size = len(data)
        archive.addfile(plain, io.BytesIO(data))

    problems = "\n".join(distribution.check_archive(path))

    assert "binary" in problems or "ELF" in problems
    assert "THIRD_PARTY_NOTICES" in problems


def _package(root: Path, *, dependencies: str, recorded: str, notices: str = "x") -> Path:
    package = root / "packages" / "p"
    package.mkdir(parents=True)
    (package / "pyproject.toml").write_text(
        f'[project]\nname = "p"\ndependencies = [{dependencies}]\n',
        encoding="utf-8",
    )
    fields = (
        'name = "d"\nspdx = "MIT"\nsource = "s"\nverified_version = "1"\n'
        'verified_on = "2026-11-04"\nevidence = "e"\n'
    )
    (package / "licenses.toml").write_text(
        f'[[dependency]]\nrequirement = "{recorded}"\n{fields}',
        encoding="utf-8",
    )
    (package / "THIRD_PARTY_NOTICES.md").write_text(notices, encoding="utf-8")
    return package


def test_a_changed_dependency_fails_until_the_license_record_follows(tmp_path):
    package = _package(tmp_path, dependencies='"d>=2,<3"', recorded="d>=1,<2", notices="d>=2,<3")
    assert "licenses.toml has" in "\n".join(licenses.check_package(package))


def test_notices_must_mention_each_dependency(tmp_path):
    package = _package(tmp_path, dependencies='"d>=1,<2"', recorded="d>=1,<2", notices="nothing")
    assert "notices do not mention" in "\n".join(licenses.check_package(package))


def test_consistent_records_pass(tmp_path):
    package = _package(tmp_path, dependencies='"d>=1,<2"', recorded="d>=1,<2", notices="d>=1,<2")
    assert licenses.check_package(package) == []


def test_every_package_here_matches_its_records():
    for package in licenses.packages():
        assert licenses.check_package(package) == []


def test_no_binary_or_foreign_files_are_tracked_in_the_repository():
    allowed = {".md", ".py", ".sql", ".toml", ".txt", ".json", ".patch", ""}
    for path in ROOT.rglob("*"):
        parts = set(path.relative_to(ROOT).parts)
        if path.is_dir() or parts & {".git", ".venv", "__pycache__", "dist", ".pytest_cache"}:
            continue
        if parts & {".ruff_cache", ".mypy_cache"}:
            continue
        assert path.suffix in allowed, path
        assert b"\0" not in path.read_bytes(), path


def test_the_catalog_matches_the_repository():
    assert catalog.validate(catalog.load()) == []


def test_listing_the_catalog_imports_no_plugin():
    import subprocess

    tool = str(ROOT / "tools" / "catalog.py")
    plugins = {"tarel", "tarel_connector_oracle", "oracledb", "pymssql", "sqlglot", "llama_cpp"}
    code = (
        "import sys, runpy\n"
        "sys.argv = ['catalog', 'list']\n"
        "try:\n"
        f"    runpy.run_path({tool!r}, run_name='__main__')\n"
        "except SystemExit:\n"
        "    pass\n"
        f"print(sorted(m for m in sys.modules if m.split('.')[0] in {plugins!r}))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip().splitlines()[-1] == "[]"
    assert "connector-oracle" in done.stdout


def test_a_catalog_entry_cannot_claim_what_the_package_does_not_declare(tmp_path):
    root = tmp_path
    package = root / "packages" / "q"
    package.mkdir(parents=True)
    (package / "pyproject.toml").write_text(
        '[project]\nname = "q"\ndependencies = ["other>=1,<2"]\n',
        encoding="utf-8",
    )
    entry = {
        "id": "q",
        "capabilities": ["connector"],
        "dependencies": ["wanted>=1,<2"],
        "entry_point": {"group": "tarel.connectors", "name": "q"},
        "host_contract": "connector.v1",
        "host_versions": "x",
        "import_name": "q",
        "install": "x",
        "license": "x",
        "native_requirements": [],
        "origin": "x",
        "package": "q",
        "path": "packages/q",
        "real_source_evidence": "x",
        "status": "experimental",
    }

    problems = "\n".join(catalog.validate([entry], root=root))

    assert "no such entry point" in problems
    assert "catalog lists" in problems


def test_a_planned_entry_cannot_pretend_to_be_a_package(tmp_path):
    (tmp_path / "packages").mkdir()
    entry = {"id": "z", "status": "planned", "package": "z"}
    assert "must not name a package" in "\n".join(catalog.validate([entry], root=tmp_path))


def test_duplicate_wheel_entry_cannot_hide_its_first_payload(tmp_path):
    wheel = _wheel(tmp_path / "x.whl")
    with zipfile.ZipFile(wheel, "a") as archive, pytest.warns(UserWarning, match="Duplicate"):
        archive.writestr("tarel_x/__init__.py", b"\x7fELFhidden")
    problems = " ".join(distribution.check_archive(wheel))
    assert "duplicate archive path" in problems and "ELF binary" in problems


def test_catalog_package_path_cannot_follow_external_symlink(tmp_path):
    package_root = tmp_path / "packages"
    package_root.mkdir()
    (package_root / "redirect").symlink_to(tmp_path)
    entry = dict(catalog.load()[0], path="packages/redirect")
    assert "escapes" in " ".join(catalog.validate([entry], root=tmp_path))
