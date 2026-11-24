# TAREL-HUB

Lokales Arbeitsrepository für gezielt installierbare TAREL-Erweiterungen.
Priorität: schneller Einstieg mit SQL-Server-/Oracle-Connectoren; danach
Dokument-/ETL-Importer, lokale Embeddings, Reranking und SQL-Lineage.

**Stand:** Erste Bausteine, nichts freigegeben oder veröffentlicht. Was wirklich belegt ist, steht in
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

| Wo | Was |
| --- | --- |
| [DuckDB](packages/connector-duckdb/README.md) und [MongoDB](packages/connector-mongodb/README.md) | Metadaten-Connectoren mit echtem Datenbanktest, siehe [Sicherheits- und Funktionsprüfung](docs/hub-review.md) |
| [PostgreSQL](packages/connector-postgres/README.md), [MySQL/MariaDB](packages/connector-mysql/README.md), [ClickHouse](packages/connector-clickhouse/README.md), [Oracle](packages/connector-oracle/README.md) | Metadaten-Connectoren, geprüft gegen echte Server, siehe [echte Quellen](docs/real-source-tests.md) |
| `catalog/catalog.toml` | Was es gibt und wie weit es ist; `python tools/catalog.py list` |
| [docs/inventory.md](docs/inventory.md) | Bestandsaufnahme von Host, Verträgen und Lizenzen |
| [docs/host-proposals](docs/host-proposals) | Offene Vorschläge an den Host |
| [docs/dependency-policy.md](docs/dependency-policy.md) | Was die Prüfungen leisten und was nicht |
| [Auftrag und Spezifikation](OPUS_IMPLEMENTATION_PROMPT.md) | Der vollständige Arbeitsauftrag |

Installiert wird immer ein einzelnes Paket, nie der ganze Hub.

## Referenz und Grenzen

Host ist der öffentliche `tarel` (PyPI, `mpsgitai/tarel`). Die Hub-Tests liefen am
24.11.2026 gegen `tarel 0.0.5`: 96 bestanden, 1 übersprungen. Die Inventare und
Kompatibilitätsdateien beschreiben noch den Stand gegen 0.0.3.

Eigener Adaptercode gehört in den Hub. Externe Bibliotheken werden als Dependencies
bezogen; Modelle separat und ausdrücklich heruntergeladen. Kundendokumente und
ETL-Quellen gehören in autorisierte private Projekt-States, nicht in dieses Repo.

Installation eines Plugins bedeutet weder automatische Aktivierung noch Sandbox-
Isolation. Die Kernregeln von TAREL gelten für alle Erweiterungen.

Eigener Code im Hub steht unter MIT (Rechteinhaber MPS, wie TAREL); jedes Paket trägt
eine eigene `LICENSE`. Fremdlizenzen bleiben eigenständig gültig und werden nur verlinkt.
Bis zur Entscheidung über PyPI tragen die Pakete weiter `Private :: Do Not Upload`.
Das Repo startet privat als `mpsgitai/tarel-hub`.
