"""Read structural metadata from PostgreSQL through pg_catalog, inside a read-only transaction."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlsplit

from tarel.connectors.contracts import (
    CatalogField,
    CatalogObject,
    CatalogRelationship,
    CatalogRequest,
    CatalogResult,
    ConnectorFailure,
    ConnectorManifest,
    ProbeRequest,
    ProbeResult,
    SampleRequest,
    SampleResult,
)

# Only objects the login may select are reported; partitions appear through their parent.
_OBJECTS = """
SELECT n.nspname, c.relname, c.relkind IN ('v', 'm'), obj_description(c.oid, 'pg_class')
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'f', 'v', 'm') AND NOT c.relispartition
AND n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg\\_%%'
AND has_any_column_privilege(c.oid, 'SELECT')
AND (%(ns)s::text IS NULL OR n.nspname = %(ns)s::text)
ORDER BY n.nspname, c.relname
"""
_COLUMNS = """
SELECT n.nspname, c.relname, a.attname, a.attnum, format_type(a.atttypid, a.atttypmod),
       NOT a.attnotnull, col_description(c.oid, a.attnum)
FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE a.attnum > 0 AND NOT a.attisdropped
AND c.relkind IN ('r', 'p', 'f', 'v', 'm') AND NOT c.relispartition
AND has_any_column_privilege(c.oid, 'SELECT')
AND (%(ns)s::text IS NULL OR n.nspname = %(ns)s::text)
ORDER BY n.nspname, c.relname, a.attnum
"""
_CONSTRAINTS = """
SELECT k.contype, k.conname, n.nspname, c.relname, rn.nspname, r.relname,
       array(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY u(n, i)
             JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = u.n ORDER BY u.i),
       array(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY u(n, i)
             JOIN pg_attribute a ON a.attrelid = k.confrelid AND a.attnum = u.n ORDER BY u.i)
FROM pg_constraint k JOIN pg_class c ON c.oid = k.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_class r ON r.oid = k.confrelid LEFT JOIN pg_namespace rn ON rn.oid = r.relnamespace
WHERE k.contype IN ('p', 'f') AND has_any_column_privilege(c.oid, 'SELECT')
AND (%(ns)s::text IS NULL OR n.nspname = %(ns)s::text)
ORDER BY n.nspname, c.relname, k.conname
"""
_PROBE = "SELECT current_setting('server_version'), nullif(current_setting('cluster_name'), '')"


def _one(conn: Any, query: str) -> tuple[Any, ...]:
    row = conn.execute(query).fetchone()
    if row is None:
        raise ConnectorFailure("source_failed", "PostgreSQL returned no metadata.")
    return tuple(row)


@contextmanager
def _session(request: ProbeRequest | CatalogRequest) -> Iterator[tuple[Any, str]]:
    import psycopg

    if urlsplit(request.url).scheme not in {"postgresql", "postgres"}:
        raise ConnectorFailure("unsupported_url", "PostgreSQL requires a postgresql:// URL.")
    options: dict[str, str | int] = {"connect_timeout": 5, "options": "-c statement_timeout=30000"}
    if request.database:
        options["dbname"] = request.database
    try:
        # A missing password is left to libpq: pgpass, SSPI, GSSAPI or peer authentication.
        conninfo = psycopg.conninfo.make_conninfo(request.url, **options)
        conn = psycopg.connect(conninfo, autocommit=False)
    except psycopg.Error:
        # libpq reports refused logins, unknown databases and unreachable hosts alike and in the
        # server's language, so the message is not parsed and never shown.
        raise ConnectorFailure(
            "connection_failed", "PostgreSQL connection or login failed."
        ) from None
    try:
        with conn:
            conn.read_only = True
            database = _one(conn, "SELECT current_database()")[0]
            yield conn, database
            conn.rollback()
    except psycopg.Error:
        raise ConnectorFailure("source_failed", "PostgreSQL metadata access failed.") from None


class PostgresConnector:
    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    def probe(self, request: ProbeRequest) -> ProbeResult:
        with _session(request) as (conn, database):
            version, server = _one(conn, _PROBE)
        return ProbeResult(
            "postgres",
            "postgres",
            server,
            database,
            version,
            None,
            None,
            self.manifest.capabilities,
        )

    def discover_catalog(self, request: CatalogRequest) -> CatalogResult:
        scope = {"ns": request.namespace}
        with _session(request) as (conn, database):
            objects = conn.execute(_OBJECTS, scope).fetchall()
            columns = conn.execute(_COLUMNS, scope).fetchall()
            constraints = conn.execute(_CONSTRAINTS, scope).fetchall()
        keys = {(s, t): tuple(cols) for kind, _, s, t, _, _, cols, _ in constraints if kind == "p"}
        fields: dict[tuple[str, str], list[CatalogField]] = {}
        for schema, table, name, position, data_type, nullable, description in columns:
            fields.setdefault((schema, table), []).append(
                CatalogField(
                    name,
                    position,
                    data_type,
                    nullable,
                    description,
                    name in keys.get((schema, table), ()),
                )
            )
        catalog_objects = tuple(
            CatalogObject(
                schema,
                table,
                "view" if is_view else "table",
                tuple(fields.get((schema, table), ())),
                description,
                keys.get((schema, table), ()),
            )
            for schema, table, is_view, description in objects
        )
        visible = {(item.namespace, item.name) for item in catalog_objects}
        relationships = tuple(
            CatalogRelationship(name, s, t, tuple(cols), rs, rt, tuple(ref_cols))
            for kind, name, s, t, rs, rt, cols, ref_cols in constraints
            if kind == "f" and (rs, rt) in visible
        )
        return CatalogResult(
            "postgres", "postgres", database, "postgres", catalog_objects, relationships
        )

    def sample_rows(self, request: SampleRequest) -> SampleResult:
        raise ConnectorFailure("unsupported_capability", "PostgreSQL metadata only.")


def create_connector(manifest: ConnectorManifest) -> PostgresConnector:
    return PostgresConnector(manifest)
