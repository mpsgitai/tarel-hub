"""Build one package and prove it in fresh environments outside this repository.

    python tools/verify_install.py connector-oracle [--host ../tarel] [--public-host 0.0.6]

Nothing here uses an editable install or the repository on ``PYTHONPATH``, except for the scripted
fake driver in steps labelled MOCK. Results go to ``docs/compatibility/<package>.json`` with the
host commit and dirty state, because a host version number alone does not identify its contracts.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_OTHER_DRIVERS = ("pymssql", "llama_cpp", "sqlglot", "sqlite_vec", "yaml", "torch")
_SECRET = "s3cr3t-do-not-show"
_FAKE_SCENARIO = {
    "columns": [
        ["HR", "EMPLOYEES", "TABLE", "ID", 1, "NUMBER", 22, 0, None, 10, 0, "N", None, None],
        ["HR", "DEPARTMENTS", "TABLE", "ID", 1, "NUMBER", 22, 0, None, 10, 0, "N", None, None],
    ],
    "foreign_keys": [],
    "primary_keys": [["HR", "EMPLOYEES", "ID"]],
    "probe": [["dbhost", "ORCLCDB"]],
}


@dataclass(slots=True)
class Report:
    checks: list[dict[str, Any]] = field(default_factory=list)

    def add(self, name: str, passed: bool, kind: str, detail: object = "") -> None:
        self.checks.append({"evidence": kind, "name": name, "passed": passed})
        print(
            f"{'PASS' if passed else 'FAIL'}  [{kind}] {name}"
            + (f"  {detail}" if not passed else "")
        )

    @property
    def failed(self) -> int:
        return sum(not item["passed"] for item in self.checks)


def _run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)


def _environment(work: Path, name: str, *requirements: str) -> Path:
    """A fresh virtual environment holding exactly these requirements and what they need."""
    directory = work / name
    created = _run(["uv", "venv", "-q", "--python", "3.12", str(directory)])
    if created.returncode:
        raise SystemExit(created.stderr)
    python = directory / "bin" / "python"
    if requirements:
        installed = _run(["uv", "pip", "install", "-q", "--python", str(python), *requirements])
        if installed.returncode:
            raise SystemExit(installed.stderr)
    return python


def _clean_env(**extra: str) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("TAREL_")}
    environment.pop("PYTHONPATH", None)
    environment.update(extra)
    return environment


def _tarel(
    python: Path, *arguments: str, cwd: Path, **extra: str
) -> subprocess.CompletedProcess[str]:
    return _run([str(python), "-m", "tarel", *arguments], cwd=cwd, env=_clean_env(**extra))


def _offline_prefix() -> list[str]:
    if shutil.which("unshare") and _run(["unshare", "-rn", "true"]).returncode == 0:
        return ["unshare", "-rn"]
    return []


def host_identity(host: Path) -> dict[str, Any]:
    commit = _run(["git", "-C", str(host), "rev-parse", "HEAD"]).stdout.strip()
    dirty = bool(_run(["git", "-C", str(host), "status", "--porcelain"]).stdout.strip())
    return {"commit": commit, "dirty": dirty}


def verify_minimal_host(host_wheel: Path, work: Path, report: Report) -> None:
    python = _environment(work, "host-only", str(host_wheel))
    cwd = work / "cwd"
    version = _tarel(python, "version", cwd=cwd)
    report.add("host alone installs and starts", version.returncode == 0, "real", version.stderr)
    check = (
        "import importlib.util as u;"
        f"print([n for n in {('oracledb', *_OTHER_DRIVERS)!r} if u.find_spec(n)])"
    )
    absent = _run([str(python), "-c", check], cwd=cwd, env=_clean_env())
    report.add(
        "host alone brings no optional driver", absent.stdout.strip() == "[]", "real", absent.stdout
    )
    unknown = _tarel(python, "connector", "check", "oracle", cwd=cwd)
    report.add(
        "without the package the host does not know oracle",
        unknown.returncode != 0 and "unknown_connector" in unknown.stderr,
        "real",
        unknown.stderr,
    )


def verify_connector(
    python: Path,
    package: Path,
    work: Path,
    report: Report,
    *,
    label: str,
) -> None:
    cwd = work / "cwd"
    where = _run(
        [str(python), "-c", "import tarel_connector_oracle as m; print(m.__file__)"],
        cwd=cwd,
        env=_clean_env(),
    ).stdout.strip()
    report.add(
        f"{label}: imported from the environment, not this repository",
        bool(where) and str(python.parent.parent) in where and str(ROOT) not in where,
        "real",
        where,
    )
    check = _tarel(python, "connector", "check", "oracle", "--format", "json", cwd=cwd)
    data = json.loads(check.stdout) if check.returncode == 0 else {}
    report.add(
        f"{label}: connector check finds it", data.get("available") is True, "real", check.stderr
    )

    code = (
        "import sys;"
        "from tarel.connectors.host import check_connector;"
        "check_connector('oracle');"
        "print('oracledb' in sys.modules)"
    )
    lazy = _run([str(python), "-c", code], cwd=cwd, env=_clean_env())
    report.add(
        f"{label}: discovery imports no driver", lazy.stdout.strip() == "False", "real", lazy.stderr
    )

    absent_code = (
        f"import importlib.util as u;print([n for n in {_OTHER_DRIVERS!r} if u.find_spec(n)])"
    )
    absent = _run([str(python), "-c", absent_code], cwd=cwd, env=_clean_env())
    report.add(
        f"{label}: other drivers stay absent", absent.stdout.strip() == "[]", "real", absent.stdout
    )

    prefix = _offline_prefix()
    if prefix:
        offline = _run(
            [*prefix, str(python), "-m", "tarel", "connector", "check", "oracle"],
            cwd=cwd,
            env=_clean_env(),
        )
        report.add(
            f"{label}: discovery works without a network",
            offline.returncode == 0,
            "real",
            offline.stderr,
        )
    else:
        report.add(f"{label}: discovery without a network", True, "not-isolated-here")

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"oracle://scott:{_SECRET}@127.0.0.1:{port}/NOPE"
    refused = _tarel(python, "connector", "probe", "oracle", cwd=cwd, TAREL_ORACLE_URL=url)
    report.add(
        f"{label}: real driver, closed port: clean failure, no secret",
        refused.returncode != 0
        and "connection_failed" in refused.stderr
        and _SECRET not in refused.stderr + refused.stdout,
        "real-driver-no-database",
        refused.stderr,
    )

    _verify_graph_with_fake_driver(python, package, work, report, label)


def _verify_graph_with_fake_driver(
    python: Path,
    package: Path,
    work: Path,
    report: Report,
    label: str,
) -> None:
    state = work / f"state-{label}"
    state.mkdir()
    scenario = state / "scenario.json"
    scenario.write_text(json.dumps(_FAKE_SCENARIO), encoding="utf-8")
    config = state / "source.toml"
    config.write_text(
        f'[oracle]\nurl = "oracle://scott:{_SECRET}@db.example.test:1521/ORCLCDB"\n',
        encoding="utf-8",
    )
    extra = {
        "FAKE_ORACLE_SCENARIO": str(scenario),
        "PYTHONPATH": str(package / "tests" / "fake_driver"),
    }
    build = _tarel(
        python,
        "graph",
        "build",
        "hr",
        "--connector",
        "oracle",
        "--config",
        str(config),
        cwd=state,
        **extra,
    )
    report.add(
        f"{label}: first graph through the real CLI",
        build.returncode == 0,
        "mock-driver",
        build.stderr,
    )
    graph_path = state / ".tarel" / "graphs" / "hr" / "graph.json"
    text = graph_path.read_text("utf-8") if graph_path.exists() else ""
    report.add(
        f"{label}: graph holds objects and no connection details",
        "HR.EMPLOYEES" in text and _SECRET not in text and "db.example.test" not in text,
        "mock-driver",
    )
    refresh = _tarel(
        python,
        "graph",
        "refresh",
        "hr",
        "--config",
        str(config),
        "--format",
        "json",
        cwd=state,
        **extra,
    )
    report.add(
        f"{label}: refresh through the real CLI",
        refresh.returncode == 0,
        "mock-driver",
        refresh.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", choices=["connector-oracle"], help="Oracle scenario runner")
    parser.add_argument("--host", type=Path, default=ROOT.parent / "tarel")
    parser.add_argument(
        "--public-host", help="Also test against this version from the package index."
    )
    args = parser.parse_args()
    package = ROOT / "packages" / args.package
    report = Report()
    with tempfile.TemporaryDirectory(prefix="tarel-hub-verify-") as temporary:
        work = Path(temporary)
        (work / "cwd").mkdir()
        dist = work / "dist"
        built = _run(["uv", "build", "-q", str(package), "--out-dir", str(dist)])
        report.add("wheel and sdist build", built.returncode == 0, "real", built.stderr)
        checked = _run([sys.executable, str(ROOT / "tools" / "check_distribution.py"), str(dist)])
        report.add("distribution rules pass", checked.returncode == 0, "real", checked.stdout)
        print(checked.stdout.rstrip())
        licenses = _run([sys.executable, str(ROOT / "tools" / "check_licenses.py")])
        report.add(
            "license records match the dependencies",
            licenses.returncode == 0,
            "real",
            licenses.stdout,
        )

        host_dist = work / "host-dist"
        host_built = _run(
            ["uv", "build", "-q", str(args.host), "--wheel", "--out-dir", str(host_dist)]
        )
        if host_built.returncode:
            raise SystemExit(host_built.stderr)
        host_wheel = next(host_dist.glob("*.whl"))
        wheel = next(dist.glob("*.whl"))
        sdist = next(dist.glob("*.tar.gz"))

        verify_minimal_host(host_wheel, work, report)
        python = _environment(work, "with-package", str(host_wheel), str(wheel))
        verify_connector(python, package, work, report, label="local-host")
        inventory = _run(
            [
                sys.executable,
                str(ROOT / "tools" / "check_licenses.py"),
                "--inventory",
                args.package,
                "--python",
                str(python),
            ],
        )
        report.add(
            "resolved dependencies inventoried", inventory.returncode == 0, "real", inventory.stderr
        )

        from_sdist = _environment(work, "from-sdist", str(host_wheel), str(sdist))
        report.add(
            "the sdist installs too",
            _tarel(from_sdist, "connector", "check", "oracle", cwd=work / "cwd").returncode == 0,
            "real",
        )
        public_result = None
        if args.public_host:
            public = _environment(work, "public-host", f"tarel=={args.public_host}", str(wheel))
            before = report.failed
            verify_connector(public, package, work, report, label=f"public-{args.public_host}")
            public_result = {"passed": report.failed == before, "version": args.public_host}
        versions = _run(
            ["uv", "pip", "list", "--python", str(python), "--format", "json"],
        )
        resolved = {item["name"]: item["version"] for item in json.loads(versions.stdout)}

    target = ROOT / "docs" / "compatibility" / f"{args.package}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "checks": report.checks,
                "host": host_identity(args.host),
                "public_host": public_result,
                "real_database": "not run by verify_install.py (see docs/real-source-tests.md)",
                "resolved_versions": resolved,
                "tested_on": datetime.now(UTC).strftime("%Y-%m-%d"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(report.checks)} checks, {report.failed} failed")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
