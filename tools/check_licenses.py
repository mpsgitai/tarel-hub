"""Tie each package's declared dependencies to its license record and its resolved inventory.

    python tools/check_licenses.py                     # compare every package with its records
    python tools/check_licenses.py --inventory PKG --python VENV/bin/python
                                                       # write what that environment really holds

Changing a dependency without updating ``licenses.toml`` fails here. An inventory lists what one
platform resolved, including native libraries inside wheels. A component without a recognisable
license is an open finding, not a pass. This produces evidence, not legal advice.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = frozenset(
    {"name", "requirement", "spdx", "source", "verified_version", "verified_on", "evidence"}
)
_INVENTORY_SCRIPT = r"""
import json, re
from importlib.metadata import distributions

def license_of(dist):
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression, "License-Expression"
    classifiers = [
        item.split("::")[-1].strip()
        for item in meta.get_all("Classifier") or []
        if item.startswith("License ::")
    ]
    if classifiers:
        return " AND ".join(classifiers), "classifier"
    text = (meta.get("License") or "").strip()
    if text:
        return text.splitlines()[0].strip()[:80], "License field"
    return None, None

rows = []
for dist in distributions():
    name = dist.metadata["Name"]
    files = [str(item) for item in (dist.files or [])]
    native = sorted(
        item for item in files
        if item.endswith((".so", ".pyd", ".dll", ".dylib")) or re.search(r"\.so\.", item)
    )
    shipped = sorted(
        item for item in files
        if re.search(r"(licen[cs]e|notice|copying)", item.split("/")[-1], re.I)
        or "/licenses/" in item
    )
    license_text, basis = license_of(dist)
    rows.append({
        "name": name,
        "version": dist.version,
        "license": license_text,
        "license_basis": basis,
        "license_files": shipped,
        "native_files": native,
    })
print(json.dumps(sorted(rows, key=lambda row: row["name"].casefold())))
"""


def packages() -> list[Path]:
    return sorted(path.parent for path in (ROOT / "packages").glob("*/pyproject.toml"))


def check_package(package: Path) -> list[str]:
    project = tomllib.loads((package / "pyproject.toml").read_text("utf-8"))["project"]
    record_path = package / "licenses.toml"
    if not record_path.is_file():
        return [f"{package.name}: licenses.toml is missing"]
    records = tomllib.loads(record_path.read_text("utf-8")).get("dependency", [])
    problems = []
    for record in records:
        missing = REQUIRED_FIELDS - set(record)
        if missing:
            problems.append(f"{package.name}: {record.get('name')} lacks {sorted(missing)}")
    declared = sorted(project.get("dependencies", []))
    recorded = sorted(str(record.get("requirement")) for record in records)
    if declared != recorded:
        problems.append(f"{package.name}: pyproject has {declared}, licenses.toml has {recorded}")
    notices = package / "THIRD_PARTY_NOTICES.md"
    if not notices.is_file():
        problems.append(f"{package.name}: THIRD_PARTY_NOTICES.md is missing")
    else:
        text = notices.read_text("utf-8")
        for requirement in declared:
            if requirement not in text:
                problems.append(f"{package.name}: notices do not mention {requirement}")
    return problems


def write_inventory(package: Path, python: str) -> Path:
    done = subprocess.run(
        [python, "-I", "-c", _INVENTORY_SCRIPT],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = json.loads(done.stdout)
    tag = f"{sys.platform}-{platform.machine()}-py{sys.version_info.major}{sys.version_info.minor}"
    target = package / f"dependency-inventory.{tag}.json"
    payload = {
        "note": "What one fresh environment resolved. Evidence for review, not legal advice.",
        "open_findings": [row["name"] for row in rows if not row["license"]],
        "platform": tag,
        "resolved": rows,
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inventory", help="Package directory name to write an inventory for.")
    parser.add_argument("--python", help="Interpreter of the environment to inventory.")
    args = parser.parse_args()
    if args.inventory:
        if not args.python:
            parser.error("--inventory needs --python")
        print(write_inventory(ROOT / "packages" / args.inventory, args.python))
        return 0
    problems = [problem for package in packages() for problem in check_package(package)]
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"{len(packages())} packages checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
