"""List and validate the extension catalog. This never imports a plugin or touches the network.

python tools/catalog.py list
python tools/catalog.py show connector-oracle
python tools/catalog.py validate
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "catalog.toml"
CATALOG_JSON = ROOT / "catalog" / "catalog.json"
HUB_GIT_BASE = "git+https://github.com/mpsgitai/tarel-hub.git"
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


def _infer_kind(entry: dict[str, Any]) -> str:
    capabilities = set(entry.get("capabilities", []))
    if "connector" in capabilities:
        return "connector"
    if "lineage-analysis" in capabilities:
        return "lineage"
    if "embeddings" in capabilities or "reranking" in capabilities:
        return "retrieval"
    if "importer" in capabilities:
        return "importer"
    return "extension"


def _package_extras(entry: dict[str, Any], root: Path) -> list[str]:
    rel_path = entry.get("path")
    if not rel_path:
        return []
    pyproject = root / str(rel_path) / "pyproject.toml"
    if not pyproject.is_file():
        return []
    project = tomllib.loads(pyproject.read_text("utf-8")).get("project", {})
    return sorted(project.get("optional-dependencies", {}).keys())


def build_json_catalog(entries: list[dict[str, Any]], root: Path = ROOT) -> dict[str, Any]:
    """Build the canonical machine-readable catalog.json payload from catalog.toml."""
    items: list[dict[str, Any]] = []
    for entry in entries:
        if "entry_points" in entry:
            eps = [{"group": ep["group"], "name": ep["name"]} for ep in entry["entry_points"]]
        elif "entry_point" in entry:
            ep = entry["entry_point"]
            eps = [{"group": ep["group"], "name": ep["name"]}]
        else:
            eps = []
        extras = _package_extras(entry, root)
        rel_path = entry.get("path")
        install_spec = f"{HUB_GIT_BASE}#subdirectory={rel_path}" if rel_path else None
        recommended_extra: str | None = None
        if extras and "binary" in extras and "[binary]" in str(entry.get("install", "")):
            recommended_extra = "binary"
        items.append(
            {
                "id": entry["id"],
                "kind": _infer_kind(entry),
                "capabilities": list(entry.get("capabilities", [])),
                "status": entry["status"],
                "package": entry.get("package"),
                "import_name": entry.get("import_name"),
                "path": rel_path,
                "entry_points": eps,
                "host_contract": entry["host_contract"],
                "host_versions": entry.get("host_versions"),
                "dependencies": list(entry.get("dependencies", [])),
                "native_requirements": list(entry.get("native_requirements", [])),
                "extras": extras,
                "recommended_extra": recommended_extra,
                "license": entry["license"],
                "origin": entry["origin"],
                "install": entry["install"],
                "install_spec": install_spec,
                "real_source_evidence": entry["real_source_evidence"],
            }
        )
    return {"contract_version": 1, "extensions": items}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("id")
    commands.add_parser("validate")
    export_json = commands.add_parser("export-json")
    export_json.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if catalog/catalog.json is out of date.",
    )
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
    if args.command == "export-json":
        rendered = json.dumps(build_json_catalog(entries), indent=2, sort_keys=True) + "\n"
        if args.check:
            if not CATALOG_JSON.is_file() or CATALOG_JSON.read_text("utf-8") != rendered:
                print(
                    "FAIL  catalog/catalog.json is out of date; "
                    "run `python tools/catalog.py export-json`",
                    file=sys.stderr,
                )
                return 1
            print(f"OK    {CATALOG_JSON.relative_to(ROOT)} is up to date ({len(entries)} entries)")
            return 0
        CATALOG_JSON.write_text(rendered, encoding="utf-8")
        print(f"Wrote {CATALOG_JSON.relative_to(ROOT)} ({len(entries)} entries)")
        return 0
    problems = validate(entries)
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"{len(entries)} entries, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
