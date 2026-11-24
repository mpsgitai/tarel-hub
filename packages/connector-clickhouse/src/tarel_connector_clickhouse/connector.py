"""Read structural metadata from one ClickHouse database over HTTP with readonly=1."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

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

# system.tables and system.columns only list what the login may see. The ClickHouse primary key
# is a sort key without uniqueness, so it is never reported as a primary key.
_OBJECTS = """
SELECT name, engine IN ('View', 'MaterializedView'), nullIf(comment, '')
FROM system.tables WHERE database = {db:String} AND NOT is_temporary ORDER BY name
"""
_COLUMNS = """
SELECT table, name, position, type,
  startsWith(type, 'Nullable(') OR startsWith(type, 'LowCardinality(Nullable('),
  nullIf(comment, '')
FROM system.columns WHERE database = {db:String} ORDER BY table, position
"""
_AUTHENTICATION_CODES = {"516", "192"}


@contextmanager
def _session(request: ProbeRequest | CatalogRequest) -> Iterator[tuple[Any, str]]:
    import clickhouse_connect
    from clickhouse_connect.driver.exceptions import ClickHouseError

    try:
        parsed = urlsplit(request.url)
        port = parsed.port
    except ValueError:
        raise ConnectorFailure("invalid_url", "ClickHouse connection URL is invalid.") from None
    if parsed.scheme not in {"clickhouse", "clickhouses"}:
        raise ConnectorFailure(
            "unsupported_url", "ClickHouse URLs must start with clickhouse:// or clickhouses://."
        )
    database = request.database or unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or parsed.username is None or not database:
        raise ConnectorFailure("invalid_url", "ClickHouse URLs need a user, host and database.")
    if parse_qsl(parsed.query):
        raise ConnectorFailure("invalid_url", "ClickHouse URLs take no options.")
    secure = parsed.scheme == "clickhouses"
    try:
        client = clickhouse_connect.get_client(
            host=parsed.hostname,
            port=port or (8443 if secure else 8123),
            username=unquote(parsed.username),
            password=unquote(parsed.password or ""),
            database=database,
            secure=secure,
            connect_timeout=5,
            send_receive_timeout=30,
            settings={"readonly": 1, "max_execution_time": 30},
        )
    except ClickHouseError as exc:
        kind = (
            "authentication_failed"
            if any(f"Code: {code}" in str(exc) for code in _AUTHENTICATION_CODES)
            else "connection_failed"
        )
        raise ConnectorFailure(kind, "ClickHouse connection or login failed.") from None
    try:
        yield client, database
    except ClickHouseError:
        raise ConnectorFailure("source_failed", "ClickHouse metadata access failed.") from None
    finally:
        client.close()


class ClickHouseConnector:
    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    def probe(self, request: ProbeRequest) -> ProbeResult:
        with _session(request) as (client, database):
            version, server = client.query("SELECT version(), hostName()").result_rows[0]
        return ProbeResult(
            "clickhouse",
            "clickhouse",
            server,
            database,
            version,
            None,
            None,
            self.manifest.capabilities,
        )

    def discover_catalog(self, request: CatalogRequest) -> CatalogResult:
        with _session(request) as (client, database):
            if request.namespace not in {None, database}:
                raise ConnectorFailure(
                    "invalid_scope", "In ClickHouse the namespace is the selected database."
                )
            scope = {"db": database}
            objects = client.query(_OBJECTS, parameters=scope).result_rows
            columns = client.query(_COLUMNS, parameters=scope).result_rows
        fields: dict[str, list[CatalogField]] = {}
        for table, name, position, data_type, nullable, description in columns:
            fields.setdefault(table, []).append(
                CatalogField(name, int(position), data_type, bool(nullable), description)
            )
        catalog_objects = tuple(
            CatalogObject(
                database,
                table,
                "view" if is_view else "table",
                tuple(fields.get(table, ())),
                description,
            )
            for table, is_view, description in objects
        )
        return CatalogResult("clickhouse", "clickhouse", database, "clickhouse", catalog_objects)

    def sample_rows(self, request: SampleRequest) -> SampleResult:
        raise ConnectorFailure("unsupported_capability", "ClickHouse metadata only.")


def create_connector(manifest: ConnectorManifest) -> ClickHouseConnector:
    return ClickHouseConnector(manifest)
