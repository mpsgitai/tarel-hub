"""Read-only Oracle metadata connector over python-oracledb in Thin mode.

Thin mode needs no Oracle Client, so this module never calls ``init_oracle_client``. The driver is
imported only when a connection is really wanted. Driver messages can echo connection details, so
a failure reports only the driver's error code.
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import Any, NoReturn
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

_CONNECT_TIMEOUT_SECONDS = 5.0
_PROBE_CALL_TIMEOUT_MS = 15_000
_DISCOVERY_CALL_TIMEOUT_MS = 120_000
_FETCH_BATCH = 5_000
_DRIVER_CODE = re.compile(r"^(ORA|DPY)-\d+$")

_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"
_PROBE_SQL = """
SELECT
    SYS_CONTEXT('USERENV', 'SERVER_HOST'),
    SYS_CONTEXT('USERENV', 'DB_NAME')
FROM DUAL
"""
_OWNER_FILTER = "AND users.username = :owner"
_COLUMNS_SQL = """
SELECT
    columns.owner,
    columns.table_name,
    objects.object_type,
    columns.column_name,
    columns.column_id,
    columns.data_type,
    columns.data_length,
    columns.char_length,
    columns.char_used,
    columns.data_precision,
    columns.data_scale,
    columns.nullable,
    table_comments.comments,
    column_comments.comments
FROM all_tab_columns columns
JOIN all_objects objects
  ON objects.owner = columns.owner
 AND objects.object_name = columns.table_name
 AND objects.object_type IN ('TABLE', 'VIEW')
 AND objects.subobject_name IS NULL
JOIN all_users users ON users.username = columns.owner
LEFT JOIN all_tab_comments table_comments
  ON table_comments.owner = columns.owner
 AND table_comments.table_name = columns.table_name
LEFT JOIN all_col_comments column_comments
  ON column_comments.owner = columns.owner
 AND column_comments.table_name = columns.table_name
 AND column_comments.column_name = columns.column_name
WHERE users.oracle_maintained = 'N'
  AND objects.object_name NOT LIKE 'BIN$%'
  {owner_filter}
ORDER BY columns.owner, columns.table_name, columns.column_id
"""
_PRIMARY_KEYS_SQL = """
SELECT
    constraints.owner,
    constraints.table_name,
    key_columns.column_name
FROM all_constraints constraints
JOIN all_cons_columns key_columns
  ON key_columns.owner = constraints.owner
 AND key_columns.constraint_name = constraints.constraint_name
JOIN all_users users ON users.username = constraints.owner
WHERE constraints.constraint_type = 'P'
  AND constraints.status = 'ENABLED'
  AND users.oracle_maintained = 'N'
  {owner_filter}
ORDER BY constraints.owner, constraints.table_name, key_columns.position
"""
_FOREIGN_KEYS_SQL = """
SELECT
    constraints.constraint_name,
    constraints.owner,
    constraints.table_name,
    source_columns.column_name,
    targets.owner,
    targets.table_name,
    target_columns.column_name
FROM all_constraints constraints
JOIN all_constraints targets
  ON targets.owner = constraints.r_owner
 AND targets.constraint_name = constraints.r_constraint_name
JOIN all_cons_columns source_columns
  ON source_columns.owner = constraints.owner
 AND source_columns.constraint_name = constraints.constraint_name
JOIN all_cons_columns target_columns
  ON target_columns.owner = targets.owner
 AND target_columns.constraint_name = targets.constraint_name
 AND target_columns.position = source_columns.position
JOIN all_users users ON users.username = constraints.owner
WHERE constraints.constraint_type = 'R'
  AND constraints.status = 'ENABLED'
  AND users.oracle_maintained = 'N'
  {owner_filter}
ORDER BY constraints.owner, constraints.table_name, constraints.constraint_name,
         source_columns.position
"""

_AUTHENTICATION_CODES = frozenset({"ORA-01017", "ORA-28000", "ORA-28001"})
_PRIVILEGE_CODES = frozenset({"ORA-00942", "ORA-01031", "ORA-01045"})
_UNSUPPORTED_CODES = frozenset({"ORA-00904"})


@dataclass(frozen=True, slots=True)
class _Target:
    host: str
    port: int
    user: str
    password: str
    service: str
    protocol: str

    def __repr__(self) -> str:
        return f"_Target({self.label})"

    @property
    def label(self) -> str:
        return f"{self.host}:{self.port}/{self.service}"


class OracleConnector:
    def __init__(self, manifest: ConnectorManifest) -> None:
        self.manifest = manifest

    def probe(self, request: ProbeRequest) -> ProbeResult:
        target = _parse_target(request.url, request.database)
        with _session(target, _PROBE_CALL_TIMEOUT_MS, stage="probe") as (connection, cursor):
            try:
                cursor.execute(_PROBE_SQL)
                row = cursor.fetchone()
                version = getattr(connection, "version", None)
            except Exception as exc:
                _raise_driver_failure(exc, target, "probe")
        if row is None:
            raise ConnectorFailure(
                "invalid_response", "Oracle probe returned no database identity."
            )
        return ProbeResult(
            connector=self.manifest.name,
            source_type=self.manifest.source_type,
            server_name=_optional_text(row[0]),
            database_name=target.service,
            product_version=_optional_text(version),
            product_level=None,
            edition=None,
            capabilities=self.manifest.capabilities,
        )

    def discover_catalog(self, request: CatalogRequest) -> CatalogResult:
        target = _parse_target(request.url, request.database)
        with _session(target, _DISCOVERY_CALL_TIMEOUT_MS, stage="discovery") as (_, cursor):
            try:
                column_rows = _query(cursor, _COLUMNS_SQL, request.namespace)
                primary_key_rows = _query(cursor, _PRIMARY_KEYS_SQL, request.namespace)
                foreign_key_rows = _query(cursor, _FOREIGN_KEYS_SQL, request.namespace)
            except Exception as exc:
                _raise_driver_failure(exc, target, "discovery")
        if not column_rows:
            _raise_nothing_visible(request.namespace)
        objects = _objects(column_rows, primary_key_rows)
        known = {(item.namespace, item.name) for item in objects}
        return CatalogResult(
            connector=self.manifest.name,
            source_type=self.manifest.source_type,
            catalog=target.service,
            dialect=self.manifest.dialect,
            objects=objects,
            relationships=_relationships(foreign_key_rows, known),
        )

    def sample_rows(self, request: SampleRequest) -> SampleResult:
        """Not offered: a first graph needs no rows, and this connector never reads any."""
        raise ConnectorFailure(
            "unsupported_capability",
            "The Oracle connector reads metadata only, never rows.",
        )


def create_connector(manifest: ConnectorManifest) -> OracleConnector:
    return OracleConnector(manifest)


def _driver() -> Any:
    try:
        return importlib.import_module("oracledb")
    except ImportError as exc:
        raise ConnectorFailure(
            "missing_dependency",
            "The Oracle connector needs the oracledb package; reinstall tarel-connector-oracle.",
        ) from exc


@contextmanager
def _session(target: _Target, call_timeout_ms: int, *, stage: str) -> Iterator[tuple[Any, Any]]:
    """One read-only transaction. Its connection is released however the block ends."""
    driver = _driver()
    connection: Any | None = None
    cursor: Any | None = None
    try:
        try:
            connection = driver.connect(
                user=target.user,
                password=target.password,
                host=target.host,
                port=target.port,
                service_name=target.service,
                protocol=target.protocol,
                tcp_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            )
            connection.call_timeout = call_timeout_ms
            cursor = connection.cursor()
            cursor.arraysize = _FETCH_BATCH
            cursor.execute(_READ_ONLY_SQL)
        except Exception as exc:
            _raise_driver_failure(exc, target, stage)
        yield connection, cursor
    finally:
        if cursor is not None:
            with suppress(Exception):
                cursor.close()
        if connection is not None:
            with suppress(Exception):
                connection.close()


def _query(cursor: Any, template: str, namespace: str | None) -> list[Any]:
    if namespace is None:
        cursor.execute(template.format(owner_filter=""))
    else:
        cursor.execute(template.format(owner_filter=_OWNER_FILTER), {"owner": namespace})
    return list(cursor.fetchall())


def _objects(column_rows: list[Any], primary_key_rows: list[Any]) -> tuple[CatalogObject, ...]:
    primary_keys: dict[tuple[str, str], list[str]] = {}
    for owner, table, column in primary_key_rows:
        primary_keys.setdefault((owner, table), []).append(column)
    grouped: dict[tuple[str, str], list[Any]] = {}
    for row in column_rows:
        grouped.setdefault((row[0], row[1]), []).append(row)
    objects = []
    for key in sorted(grouped):
        rows = grouped[key]
        primary_key = tuple(primary_keys.get(key, ()))
        objects.append(
            CatalogObject(
                namespace=key[0],
                name=key[1],
                kind="view" if rows[0][2] == "VIEW" else "table",
                description=_optional_text(rows[0][12]),
                primary_key=primary_key,
                fields=tuple(_field(row, primary_key) for row in rows),
            )
        )
    return tuple(objects)


def _field(row: Any, primary_key: tuple[str, ...]) -> CatalogField:
    return CatalogField(
        name=row[3],
        position=int(row[4]),
        data_type=_data_type(row[5], row[6], row[7], row[8], row[9], row[10]),
        nullable=row[11] == "Y",
        description=_optional_text(row[13]),
        is_primary_key=row[3] in primary_key,
    )


def _data_type(
    name: str,
    length: int | None,
    char_length: int | None,
    char_used: str | None,
    precision: int | None,
    scale: int | None,
) -> str:
    if name == "NUMBER" and precision is not None:
        return f"NUMBER({precision},{scale or 0})"
    if name == "FLOAT" and precision is not None:
        return f"FLOAT({precision})"
    if name in {"VARCHAR2", "CHAR"} and char_length:
        return f"{name}({char_length} {'CHAR' if char_used == 'C' else 'BYTE'})"
    if name in {"NVARCHAR2", "NCHAR"} and char_length:
        return f"{name}({char_length})"
    if name == "RAW" and length:
        return f"RAW({length})"
    return name


def _relationships(
    rows: list[Any],
    known: set[tuple[str, str]],
) -> tuple[CatalogRelationship, ...]:
    """Group one key's columns. A key into something invisible cannot be represented, so it goes."""
    grouped: dict[tuple[str, str, str], list[Any]] = {}
    for row in rows:
        grouped.setdefault((row[1], row[2], row[0]), []).append(row)
    relationships = []
    for (owner, table, name), items in sorted(grouped.items()):
        target = (items[0][4], items[0][5])
        if (owner, table) not in known or target not in known:
            continue
        relationships.append(
            CatalogRelationship(
                name=name,
                from_namespace=owner,
                from_object=table,
                from_fields=tuple(item[3] for item in items),
                to_namespace=target[0],
                to_object=target[1],
                to_fields=tuple(item[6] for item in items),
            )
        )
    return tuple(relationships)


def _parse_target(url: str, database: str | None) -> _Target:
    """Read ``oracle://user:password@host:port/service``. No error ever repeats the URL."""
    try:
        parsed = urlsplit(url)
        port = parsed.port or 1521
        query = dict(parse_qsl(parsed.query, strict_parsing=bool(parsed.query)))
    except ValueError:
        raise ConnectorFailure("invalid_url", "Oracle connection URL is invalid.") from None
    if parsed.scheme != "oracle":
        raise ConnectorFailure("unsupported_url", "Oracle URLs must start with oracle://.")
    service = database or unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or not parsed.username or parsed.password is None or not service:
        raise ConnectorFailure(
            "invalid_url",
            "Oracle URLs need a user, password, host and service name.",
        )
    protocol = query.pop("protocol", "tcp")
    if query or protocol not in {"tcp", "tcps"}:
        raise ConnectorFailure(
            "invalid_url",
            "The only Oracle URL option is protocol, with tcp or tcps.",
        )
    return _Target(
        host=parsed.hostname,
        port=port,
        user=unquote(parsed.username),
        password=unquote(parsed.password),
        service=service,
        protocol=protocol,
    )


def _raise_driver_failure(exc: Exception, target: _Target, stage: str) -> NoReturn:
    code = _driver_code(exc)
    if code in _AUTHENTICATION_CODES:
        kind = "authentication_failed"
    elif code in _PRIVILEGE_CODES:
        kind = "insufficient_privileges"
    elif code in _UNSUPPORTED_CODES or (code or "").startswith("DPY-30"):
        kind = "unsupported_source"
    elif code is not None and (code.startswith(("DPY-6", "ORA-125")) or code == "ORA-12170"):
        kind = "connection_failed"
    else:
        kind = "connection_failed" if stage == "probe" else "discovery_failed"
    detail = code or type(exc).__name__
    # "from None": the driver's own message stays out of any traceback a caller logs.
    raise ConnectorFailure(kind, f"Oracle {stage} failed for {target.label} ({detail}).") from None


def _driver_code(exc: Exception) -> str | None:
    for argument in exc.args:
        code = getattr(argument, "full_code", None)
        if isinstance(code, str) and _DRIVER_CODE.fullmatch(code):
            return code
    return None


def _raise_nothing_visible(namespace: str | None) -> NoReturn:
    if namespace is None:
        raise ConnectorFailure(
            "no_visible_objects",
            "This account sees no tables or views outside Oracle-maintained schemas.",
        )
    raise ConnectorFailure(
        "namespace_not_found",
        f"No visible objects in schema {namespace}. Names are exact, including case; "
        "it may not exist, or this account may lack rights on it.",
    )


def _optional_text(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None
