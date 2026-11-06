"""Inventory one explicitly selected MongoDB database without fetching documents."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from tarel.connectors.contracts import (
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


@contextmanager
def _database(request: ProbeRequest | CatalogRequest) -> Iterator[Any]:
    from pymongo import MongoClient

    try:
        uri = urlsplit(request.url)
        options = parse_qsl(uri.query, keep_blank_values=True, strict_parsing=True)
        allowed = {"authsource", "replicaset", "tls"}
        if (
            uri.scheme != "mongodb"
            or not uri.netloc
            or uri.fragment
            or ";" in uri.query
            or any(
                k.lower() not in allowed or (k.lower() == "tls" and v != "true") for k, v in options
            )
        ):
            raise ConnectorFailure("invalid_target", "Unsupported MongoDB URI or option.")
        with MongoClient(request.url, connect=False, timeoutMS=5000) as client:
            db = client.get_default_database(default=request.database)
            if request.database is not None and db.name != request.database:
                raise ConnectorFailure("invalid_scope", "URI and database scope differ.")
            yield db
    except ConnectorFailure:
        raise
    except Exception:
        raise ConnectorFailure("source_failed", "MongoDB metadata access failed.") from None


class MongoDBConnector:
    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    def probe(self, request: ProbeRequest) -> ProbeResult:
        with _database(request) as db:
            db.command("ping")
            return ProbeResult(
                "mongodb", "mongodb", None, db.name, None, None, None, self.manifest.capabilities
            )

    def discover_catalog(self, request: CatalogRequest) -> CatalogResult:
        with _database(request) as db:
            if request.namespace is not None and request.namespace != db.name:
                raise ConnectorFailure("invalid_scope", "MongoDB namespace must match database.")
            with db.list_collections(nameOnly=True, authorizedCollections=False) as cursor:
                objects = [
                    CatalogObject(
                        db.name, row["name"], "view" if row["type"] == "view" else "table", ()
                    )
                    for row in cursor
                    if not row["name"].startswith("system.")
                ]
            return CatalogResult(
                "mongodb",
                "mongodb",
                db.name,
                None,
                tuple(sorted(objects, key=lambda item: item.name)),
            )

    def sample_rows(self, request: SampleRequest) -> SampleResult:
        raise ConnectorFailure("unsupported_capability", "MongoDB metadata only.")


def create_connector(manifest: ConnectorManifest) -> MongoDBConnector:
    return MongoDBConnector(manifest)
