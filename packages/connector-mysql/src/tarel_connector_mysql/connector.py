"""Read structural metadata from one MySQL or MariaDB schema through information_schema."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

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

# information_schema only lists objects the login holds some privilege on.
_OBJECTS = """
SELECT TABLE_NAME, TABLE_TYPE = 'VIEW', NULLIF(TABLE_COMMENT, '')
FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
ORDER BY TABLE_NAME
"""
_COLUMNS = """
SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE = 'YES',
       NULLIF(COLUMN_COMMENT, '')
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, ORDINAL_POSITION
"""
# MariaDB hides TABLE_CONSTRAINTS from logins with object grants only, so keys come from
# KEY_COLUMN_USAGE alone: a primary key is always named PRIMARY, a foreign key has a target.
_KEYS = """
SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_SCHEMA, REFERENCED_TABLE_NAME,
       REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = %s AND (CONSTRAINT_NAME = 'PRIMARY' OR REFERENCED_TABLE_NAME IS NOT NULL)
ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION
"""
_AUTHENTICATION_CODES = {1045, 1698}


@contextmanager
def _session(request: ProbeRequest | CatalogRequest) -> Iterator[tuple[Any, str]]:
    import pymysql

    try:
        parsed = urlsplit(request.url)
        port = parsed.port or 3306
    except ValueError:
        raise ConnectorFailure("invalid_url", "MySQL connection URL is invalid.") from None
    if parsed.scheme not in {"mysql", "mariadb"}:
        raise ConnectorFailure("unsupported_url", "MySQL URLs must start with mysql://.")
    schema = request.database or unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or parsed.username is None or not schema:
        raise ConnectorFailure("invalid_url", "MySQL URLs need a user, host and schema.")
    if parse_qsl(parsed.query):
        raise ConnectorFailure("invalid_url", "MySQL URLs take no options.")
    try:
        conn = pymysql.connect(
            host=parsed.hostname,
            port=port,
            user=unquote(parsed.username),
            password=unquote(parsed.password or ""),
            database=schema,
            connect_timeout=5,
            read_timeout=30,
            charset="utf8mb4",
        )
    except pymysql.Error as exc:
        code = exc.args[0] if exc.args else None
        kind = "authentication_failed" if code in _AUTHENTICATION_CODES else "connection_failed"
        raise ConnectorFailure(kind, "MySQL connection or login failed.") from None
    except RuntimeError:
        # PyMySQL needs cryptography only for SHA-2 password login over a connection without TLS.
        raise ConnectorFailure(
            "missing_dependency",
            "MySQL SHA-2 login without TLS needs the cryptography package; "
            "enable TLS on the server or install cryptography.",
        ) from None
    try:
        with conn.cursor() as cursor:
            cursor.execute("START TRANSACTION READ ONLY")
            yield cursor, schema
        conn.rollback()
    except pymysql.Error:
        raise ConnectorFailure("source_failed", "MySQL metadata access failed.") from None
    finally:
        conn.close()


class MySqlConnector:
    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    def probe(self, request: ProbeRequest) -> ProbeResult:
        with _session(request) as (cursor, schema):
            cursor.execute("SELECT VERSION(), @@hostname")
            version, server = cursor.fetchone()
        edition = "MariaDB" if "mariadb" in version.lower() else "MySQL"
        return ProbeResult(
            "mysql",
            "mysql",
            server,
            schema,
            version,
            None,
            edition,
            self.manifest.capabilities,
        )

    def discover_catalog(self, request: CatalogRequest) -> CatalogResult:
        with _session(request) as (cursor, schema):
            if request.namespace not in {None, schema}:
                raise ConnectorFailure(
                    "invalid_scope", "In MySQL the namespace is the selected schema."
                )
            cursor.execute(_OBJECTS, (schema,))
            objects = cursor.fetchall()
            cursor.execute(_COLUMNS, (schema,))
            columns = cursor.fetchall()
            cursor.execute(_KEYS, (schema,))
            keys = cursor.fetchall()
        primary: dict[str, list[str]] = {}
        foreign: dict[tuple[str, str], list[tuple[str, str, str, str]]] = {}
        for name, table, column, ref_schema, ref_table, ref_column in keys:
            if ref_table is None:
                primary.setdefault(table, []).append(column)
            else:
                foreign.setdefault((table, name), []).append(
                    (column, ref_schema, ref_table, ref_column)
                )
        fields: dict[str, list[CatalogField]] = {}
        for table, name, position, data_type, nullable, description in columns:
            fields.setdefault(table, []).append(
                CatalogField(
                    name,
                    position,
                    data_type,
                    bool(nullable),
                    description,
                    name in primary.get(table, ()),
                )
            )
        catalog_objects = tuple(
            CatalogObject(
                schema,
                table,
                "view" if is_view else "table",
                tuple(fields.get(table, ())),
                description,
                tuple(primary.get(table, ())),
            )
            for table, is_view, description in objects
        )
        visible = {item.name for item in catalog_objects}
        relationships = tuple(
            CatalogRelationship(
                name,
                schema,
                table,
                tuple(part[0] for part in parts),
                parts[0][1],
                parts[0][2],
                tuple(part[3] for part in parts),
            )
            for (table, name), parts in foreign.items()
            if parts[0][1] == schema and parts[0][2] in visible
        )
        return CatalogResult("mysql", "mysql", schema, "mysql", catalog_objects, relationships)

    def sample_rows(self, request: SampleRequest) -> SampleResult:
        raise ConnectorFailure("unsupported_capability", "MySQL metadata only.")


def create_connector(manifest: ConnectorManifest) -> MySqlConnector:
    return MySqlConnector(manifest)
