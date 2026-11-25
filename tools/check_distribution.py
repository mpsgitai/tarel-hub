"""Check built wheels and sdists against the hub's distribution rules.

It reads what is actually inside each archive: file names and endings alone prove nothing, so
contents are checked too. A pass is evidence for a review, never a legal statement.

    python tools/check_distribution.py dist/
"""

from __future__ import annotations

import argparse
import re
import stat
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from email.parser import Parser
from pathlib import Path, PurePosixPath

ALLOWED_SUFFIXES = frozenset({".md", ".py", ".pyi", ".sql", ".toml", ".txt", ".json", ".typed"})
ALLOWED_WHEEL_METADATA = frozenset({"METADATA", "RECORD", "WHEEL", "entry_points.txt"})
PRIVATE_FILES = frozenset({"AGENTS.md", "OPUS_IMPLEMENTATION_PROMPT.md"})
VENDOR_DIRECTORIES = frozenset({"_vendor", "vendor", "vendored", "site-packages", "node_modules"})
FOREIGN_PACKAGES = frozenset(
    {
        "duckdb",
        "_duckdb",
        "pymongo",
        "bson",
        "gridfs",
        "dns",
        "oracledb",
        "pymssql",
        "sqlglot",
        "llama_cpp",
        "sqlite_vec",
        "tarel",
    }
)
BINARY_SIGNATURES = (
    (b"\x7fELF", "ELF binary"),
    (b"MZ", "Windows binary"),
    (b"\xcf\xfa\xed\xfe", "Mach-O binary"),
    (b"\xca\xfe\xba\xbe", "Mach-O binary"),
    (b"GGUF", "GGUF model"),
    (b"SQLite format 3", "SQLite database"),
    (b"PK\x03\x04", "nested archive"),
    (b"\x1f\x8b", "nested archive"),
    (b"\x93NUMPY", "NumPy array"),
)
# Assembled here so this file does not trip the check on itself.
_LOCAL_MARKERS = (
    "/" + "home/",
    "WORKSPACE_" + "2026",
    "matti" + "wsl",
    "C:\\" + "Users",
)
SECRET_PATTERNS = (
    (re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(rb"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    (re.compile(rb"\bsk-[A-Za-z0-9_-]{32,}\b"), "API key"),
    (
        re.compile(rb"[a-z+]+://[^/\s:@'\"<>{}]+:[^/\s@'\"<>{}]{3,}@[A-Za-z0-9.-]+"),
        "URL with password",
    ),
)
# A credential in a test or a document must be visibly made up.
_PLACEHOLDER_PASSWORD = re.compile(
    rb"://[^/\s:@]*:(PASSWORD|password|s3cr3t(%2Fpw)?|secret|tiger|pw)@",
)


@dataclass(frozen=True, slots=True)
class Member:
    path: str
    data: bytes


def check_archive(path: Path) -> list[str]:
    """Every rule broken by one archive, as plain sentences. An empty list is a pass."""
    if path.suffix == ".whl":
        members = list(_wheel_members(path))
        return [*_check_members(members), *_check_wheel(members)]
    if path.name.endswith(".tar.gz"):
        members = list(_sdist_members(path))
        return [*_check_members(members), *_check_sdist(members)]
    return [f"{path.name}: not a wheel or sdist"]


def _wheel_members(path: Path) -> Iterator[Member]:
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.is_dir():
                if stat.S_ISLNK(info.external_attr >> 16):
                    yield Member(info.filename, b"\x7fELF symlink is not allowed in a release")
                else:
                    yield Member(info.filename, archive.read(info))


def _sdist_members(path: Path) -> Iterator[Member]:
    with tarfile.open(path, "r:gz") as archive:
        for info in archive.getmembers():
            if info.issym() or info.islnk():
                yield Member(info.name, b"\x7fELF symlink is not allowed in a release")
            elif info.isfile():
                handle = archive.extractfile(info)
                yield Member(info.name, handle.read() if handle else b"")


def _check_members(members: list[Member]) -> list[str]:
    problems: list[str] = []
    seen: set[PurePosixPath] = set()
    for member in members:
        pure = PurePosixPath(member.path)
        where = member.path
        if pure in seen:
            problems.append(f"{where}: duplicate archive path")
        seen.add(pure)
        if pure.is_absolute() or ".." in pure.parts:
            problems.append(f"{where}: unsafe path")
        if pure.name in PRIVATE_FILES:
            problems.append(f"{where}: private project file")
        vendored = VENDOR_DIRECTORIES & set(pure.parts)
        if vendored:
            problems.append(f"{where}: vendored directory {sorted(vendored)[0]}")
        if pure.suffix not in ALLOWED_SUFFIXES and not _is_known_plain_file(pure):
            problems.append(f"{where}: file type is not on the allowlist")
        problems.extend(f"{where}: {issue}" for issue in _check_content(member))
    return problems


def _is_known_plain_file(path: PurePosixPath) -> bool:
    # Hatch always adds the project's own .gitignore to an sdist.
    return path.name in ALLOWED_WHEEL_METADATA or path.name in {"PKG-INFO", "LICENSE", ".gitignore"}


def _check_content(member: Member) -> Iterator[str]:
    for signature, label in BINARY_SIGNATURES:
        if member.data.startswith(signature):
            yield f"contains a {label}"
            return
    if b"\0" in member.data:
        yield "contains binary data"
        return
    for pattern, label in SECRET_PATTERNS:
        for match in pattern.finditer(member.data):
            if not _PLACEHOLDER_PASSWORD.search(match.group(0)):
                yield f"looks like a {label}"
                break
    text = member.data.decode("utf-8", "replace")
    for marker in _LOCAL_MARKERS:
        if marker in text:
            yield "contains a private local path"
            break


def _check_wheel(members: list[Member]) -> list[str]:
    problems: list[str] = []
    names = {member.path: member for member in members}
    metadata = next((m for p, m in names.items() if p.endswith(".dist-info/METADATA")), None)
    if metadata is None:
        return ["wheel has no METADATA"]
    parsed = Parser().parsestr(metadata.data.decode("utf-8"))
    problems.extend(_check_metadata(parsed.get_all("Requires-Dist") or []))
    if "Private :: Do Not Upload" not in (parsed.get_all("Classifier") or []) and not any(
        PurePosixPath(p).name.upper().startswith("LICENSE")
        and "/licenses/" in p
        and "PENDING" not in PurePosixPath(p).name.upper()
        for p in names
    ):
        problems.append(
            "own license is undecided, so the wheel must carry Private :: Do Not Upload"
        )
    licenses = {PurePosixPath(p).name for p in names if ".dist-info/licenses/" in p}
    if "THIRD_PARTY_NOTICES.md" not in licenses:
        problems.append("wheel lacks THIRD_PARTY_NOTICES.md under dist-info/licenses")
    if not any(name.upper().startswith("LICENSE") for name in licenses):
        problems.append("wheel lacks a license file under dist-info/licenses")
    for path in names:
        top = PurePosixPath(path).parts[0]
        if top in FOREIGN_PACKAGES:
            problems.append(f"{path}: a copy of the package {top}")
        if ".dist-info" not in path and "/tests/" in f"/{path}":
            problems.append(f"{path}: tests do not belong in a wheel")
    problems.extend(_check_manifests(names))
    return problems


def _check_manifests(names: dict[str, Member]) -> Iterator[str]:
    """A connector entry point must lead to a manifest the host can read, with the same value."""
    entry_points = next((m for p, m in names.items() if p.endswith("entry_points.txt")), None)
    if entry_points is None:
        return
    section = ""
    for raw_line in entry_points.data.decode("utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        name, separator, value = line.partition("=")
        if not separator:
            continue
        if section and section != "tarel.connectors":
            if ":" not in value:
                yield f"entry point {name.strip()} in [{section}] must use module:callable"
            continue
        module = value.strip().split(":")[0].split(".")[0]
        manifest = names.get(f"{module}/manifest.toml")
        if manifest is None:
            yield f"entry point {name.strip()} has no {module}/manifest.toml"
            continue
        declared = tomllib.loads(manifest.data.decode("utf-8")).get("connector", {})
        if declared.get("entrypoint") != value.strip() or declared.get("name") != name.strip():
            yield f"manifest of {name.strip()} disagrees with its entry point"


def _check_metadata(requirements: list[str]) -> Iterator[str]:
    for requirement in requirements:
        if "extra ==" in requirement:
            continue
        if "<" not in requirement and "==" not in requirement:
            yield f"dependency without a tested upper bound: {requirement}"


def _check_sdist(members: list[Member]) -> list[str]:
    names = {PurePosixPath(member.path).name for member in members}
    required = {"THIRD_PARTY_NOTICES.md", "licenses.toml", "pyproject.toml", "README.md"}
    problems = [f"sdist lacks {item}" for item in sorted(required - names)]
    if not any(name.upper().startswith("LICENSE") for name in names):
        problems.append("sdist lacks a license file")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    archives = sorted(
        path for path in args.directory.iterdir() if path.name.endswith((".whl", ".tar.gz"))
    )
    if not archives:
        print(f"No wheel or sdist in {args.directory}", file=sys.stderr)
        return 2
    failed = False
    for archive in archives:
        problems = check_archive(archive)
        print(f"{'FAIL' if problems else 'PASS'}  {archive.name}")
        for problem in problems:
            print(f"      {problem}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
