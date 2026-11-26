"""List and validate the extension catalog. This never imports a plugin or touches the network.

python tools/catalog.py list
python tools/catalog.py show connector-oracle
python tools/catalog.py validate
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "catalog.toml"
STATUSES = frozenset({"builtin", "experimental", "planned"})
REQUIRED = frozenset(
    {
        "capabilities",
        "dependencies",
        "host_contract",
        "id",
        "install",
        "license",
        "native_requirements",
        "origin",
        "real_source_evidence",
        "status",
    }
)
REQUIRED_WHEN_PACKAGED = frozenset(
    {"host_versions", "import_name", "package", "path"}
)


def load(path: Path = CATALOG) -> list[dict[str, Any]]:
    return tomllib.loads(path.read_text("utf-8")).get("extension", [])


def validate(entries: list[dict[str, Any]], root: Path = ROOT) -> list[str]:
    """Check what a catalog claims against what is in the repository."""
    problems: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        name = str(entry.get("id"))
        if name in seen:
            problems.append(f"{name}: duplicate id")
        seen.add(name)
        missing = REQUIRED - set(entry)
        if missing:
            problems.append(f"{name}: lacks {sorted(missing)}")
        status = entry.get("status")
        if status not in STATUSES:
            problems.append(f"{name}: unknown status {status!r}")
        if status == "experimental":
            problems.extend(_check_packaged(name, entry, root))
        if status == "planned" and (entry.get("path") or entry.get("package")):
            problems.append(f"{name}: a planned entry must not name a package")
    listed = {str(entry.get("path")) for entry in entries}
    for directory in sorted((root / "packages").glob("*/pyproject.toml")):
        relative = directory.parent.relative_to(root).as_posix()
        if relative not in listed:
            problems.append(f"{relative}: package is not in the catalog")
    return problems


def _check_packaged(name: str, entry: dict[str, Any], root: Path) -> list[str]:
    problems = []
    missing = REQUIRED_WHEN_PACKAGED - set(entry)
    if "entry_point" not in entry and "entry_points" not in entry:
        missing = missing | {"entry_point"}
    if missing:
        return [f"{name}: lacks {sorted(missing)}"]
    pyproject = root / str(entry["path"]) / "pyproject.toml"
    packages_root = (root / "packages").resolve()
    if pyproject.resolve().parent.parent != packages_root:
        return [f"{name}: package path escapes the packages directory"]
    if not pyproject.is_file():
        return [f"{name}: no package at {entry['path']}"]
    project = tomllib.loads(pyproject.read_text("utf-8"))["project"]
    if project["name"] != entry["package"]:
        problems.append(f"{name}: package name differs from {pyproject}")
    catalog_eps: set[tuple[str, str]] = set()
    if "entry_points" in entry:
        for ep in entry["entry_points"]:
            catalog_eps.add((ep["group"], ep["name"]))
    else:
        catalog_eps.add((entry["entry_point"]["group"], entry["entry_point"]["name"]))
    pyproject_eps: set[tuple[str, str]] = {
        (group, ep_name)
        for group, mapping in project.get("entry-points", {}).items()
        for ep_name in mapping
    }
    if catalog_eps != pyproject_eps:
        problems.append(
            f"{name}: catalog entry points {sorted(catalog_eps)} "
            f"differ from pyproject {sorted(pyproject_eps)}"
        )
    wanted = set(entry["dependencies"])
    actual = {item for item in project.get("dependencies", []) if not item.startswith("tarel")}
    if wanted != actual:
        problems.append(f"{name}: catalog lists {sorted(wanted)}, pyproject has {sorted(actual)}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("id")
    commands.add_parser("validate")
    args = parser.parse_args()
    entries = load()
    if args.command == "list":
        for entry in entries:
            print(f"{entry['id']:24} {entry['status']:13} {', '.join(entry['capabilities'])}")
        return 0
    if args.command == "show":
        matches = [item for item in entries if item["id"] == args.id]
        if not matches:
            print(f"Not in the catalog: {args.id}", file=sys.stderr)
            return 2
        for key, value in matches[0].items():
            print(f"{key}: {value}")
        return 0
    problems = validate(entries)
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"{len(entries)} entries, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
