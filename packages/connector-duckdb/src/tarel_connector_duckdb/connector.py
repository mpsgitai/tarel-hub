"""Read structural metadata from an explicitly selected DuckDB file."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from tarel.connectors.contracts import (
    CatalogField,
    CatalogObject,
    CatalogRequest,
    CatalogResult,
    ConnectorFailure,
    ConnectorManifest,
    ProbeRequest,
    ProbeResult,
    SampleRequest,
    SampleResult,
)

_COLUMNS = """
SELECT c.schema_name, c.table_name, v.view_name IS NOT NULL, c.column_name,
       c.column_index, c.data_type, c.is_nullable
FROM duckdb_columns() c LEFT JOIN duckdb_views() v
ON (c.database_oid, c.schema_oid, c.table_oid) = (v.database_oid, v.schema_oid, v.view_oid)
WHERE c.database_name = current_database() AND NOT c.internal
AND (? IS NULL OR c.schema_name = ?)
ORDER BY c.schema_name, c.table_name, c.column_index
"""
_KEYS = """
SELECT schema_name, table_name, constraint_column_names FROM duckdb_constraints()
WHERE database_name = current_database() AND constraint_type = 'PRIMARY KEY'
AND (? IS NULL OR schema_name = ?)
"""


@contextmanager
def _session(request: ProbeRequest | CatalogRequest) -> Iterator[tuple[Any, str]]:
    import duckdb

    try:
        value = request.url
        if value.startswith("duckdb:"):
            uri = urlsplit(value)
            if uri.netloc or uri.query or uri.fragment:
                raise ValueError
            value = unquote(uri.path)
        path = Path(value)
        if not path.is_absolute() or not path.is_file():
            raise ConnectorFailure("invalid_target", "Select an existing absolute DuckDB file.")
        settings = {
            "enable_external_access": "false",
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
        }
        with duckdb.connect(str(path), read_only=True, config=settings) as conn:
            catalog = conn.execute("SELECT current_database()").fetchone()[0]
            if request.database is not None and request.database != catalog:
                raise ConnectorFailure("invalid_scope", "The selected catalog differs.")
            yield conn, catalog
    except ConnectorFailure:
        raise
    except Exception:
        raise ConnectorFailure("source_failed", "DuckDB metadata access failed.") from None


class DuckDBConnector:
    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    def probe(self, request: ProbeRequest) -> ProbeResult:
        with _session(request) as (conn, catalog):
            version = conn.execute("SELECT version()").fetchone()[0]
        return ProbeResult(
            "duckdb", "duckdb", None, catalog, version, None, None, self.manifest.capabilities
        )

    def discover_catalog(self, request: CatalogRequest) -> CatalogResult:
        scope = [request.namespace, request.namespace]
        with _session(request) as (conn, catalog):
            conn.execute("BEGIN TRANSACTION")
            keys = {(s, t): tuple(pk) for s, t, pk in conn.execute(_KEYS, scope).fetchall()}
            rows = conn.execute(_COLUMNS, scope).fetchall()
        fields: dict[tuple[str, str, str], list[CatalogField]] = {}
        for schema, table, view, name, pos, dtype, nullable in rows:
            key = schema, table, "view" if view else "table"
            fields.setdefault(key, []).append(
                CatalogField(
                    name, pos, dtype, nullable, is_primary_key=name in keys.get((schema, table), ())
                )
            )
        objects = tuple(
            CatalogObject(s, t, k, tuple(cols), primary_key=keys.get((s, t), ()))
            for (s, t, k), cols in fields.items()
        )
        return CatalogResult("duckdb", "duckdb", catalog, "duckdb", objects)

    def sample_rows(self, request: SampleRequest) -> SampleResult:
        raise ConnectorFailure("unsupported_capability", "DuckDB metadata only.")


def create_connector(manifest: ConnectorManifest) -> DuckDBConnector:
    return DuckDBConnector(manifest)
