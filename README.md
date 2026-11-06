# TAREL-HUB

Lokales Arbeitsrepository für gezielt installierbare TAREL-Erweiterungen.
Priorität: schneller Einstieg mit SQL-Server-/Oracle-Connectoren; danach
Dokument-/ETL-Importer, lokale Embeddings, Reranking und SQL-Lineage.

**Stand:** Erste Bausteine, nichts freigegeben oder veröffentlicht. Was wirklich belegt ist, steht in
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

| Wo | Was |
| --- | --- |
| [DuckDB](packages/connector-duckdb/README.md) und [MongoDB](packages/connector-mongodb/README.md) | Metadaten-Connectoren mit echtem Datenbanktest, siehe [Sicherheits- und Funktionsprüfung](docs/hub-review.md) |
| [packages/connector-oracle](packages/connector-oracle/README.md) | Oracle-Connector, lief noch nie gegen eine echte Datenbank |
| `catalog/catalog.toml` | Was es gibt und wie weit es ist; `python tools/catalog.py list` |
| [docs/inventory.md](docs/inventory.md) | Bestandsaufnahme von Host, Verträgen und Lizenzen |
| [docs/host-proposals](docs/host-proposals) | Offene Vorschläge an den Host |
| [docs/dependency-policy.md](docs/dependency-policy.md) | Was die Prüfungen leisten und was nicht |
| [Auftrag und Spezifikation](OPUS_IMPLEMENTATION_PROMPT.md) | Der vollständige Arbeitsauftrag |

Installiert wird immer ein einzelnes Paket, nie der ganze Hub.

## Referenz und Grenzen

Der aktuelle lokale TAREL-Checkout ist `../TAREL_REFACTOR` (Großschreibung beachten).
Er dient zunächst nur als lesbare Referenz. Der frühere Pfad `../TAREL_Refactor`
existiert nicht mehr. `../TAREL_Public` bleibt unverändert.

Eigener Adaptercode gehört in den Hub. Externe Bibliotheken werden als Dependencies
bezogen; Modelle separat und ausdrücklich heruntergeladen. Kundendokumente und
ETL-Quellen gehören in autorisierte private Projekt-States, nicht in dieses Repo.

Installation eines Plugins bedeutet weder automatische Aktivierung noch Sandbox-
Isolation. Die Kernregeln von TAREL gelten für alle Erweiterungen.

Der Hub besitzt noch keine gewählte Veröffentlichungslizenz. MIT ist als Anschluss
an TAREL vorgeschlagen; vor Veröffentlichung Rechteinhaber/Lizenz bestätigen und
vollständige Lizenzdateien pro Distributionspaket ergänzen. Fremdlizenzen bleiben
eigenständig gültig. Aktuell ist kein Git-Remote eingerichtet.
