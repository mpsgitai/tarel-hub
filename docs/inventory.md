# Bestandsaufnahme: Host und Erweiterungen

Geprüft am 04.11.2026 gegen `../TAREL_REFACTOR` auf `eeb559f` (sauber) und den öffentlichen
`tarel 0.0.3`. Maßgeblich ist der gelesene Code, nicht ältere Pläne.

## Fähigkeiten

Extras installieren heute nur Fremdbibliotheken. Der Adaptercode steckt schon im Kernpaket. Eine
Installation von `tarel[sqlserver]` ist also kein externes Plugin.

| Fähigkeit | Dependency | Hostvertrag | Ladezeitpunkt heute | Hub-Baustein | Fehlender Nachweis |
| --- | --- | --- | --- | --- | --- |
| SQL Server | `pymssql>=2.3,<3` (Extra) | Connector v1, aber fest eingebaut | Im Connector-Aufruf (`sqlserver/connector.py:224`) | Kein Paket, nur Katalogeintrag: blockiert durch Vorschlag 0001 | Lizenzklärung, siehe unten |
| Oracle | `oracledb>=26.1,<27` | Connector v1 über Entry Point | Beim ersten Verbindungsaufbau | `packages/connector-oracle` | **Echte Datenbank: BLOCKIERT** |
| Provider | keine | `tarel.providers`-Entry-Point vorhanden | Beim Laden des Providers | Keiner geplant | – |
| Dokumente | keine | `add_knowledge_document_use_case`, keine Plugin-Gruppe | – | `importer-documents`, geplant | Noch nicht begonnen |
| dbt | keine (nur Standardbibliothek) | `lineage/dbt.py` eingebaut, keine Plugin-Gruppe | Mit dem Modul | Vorerst keiner | Klären, ob ein externer Importer Mehrwert hat |
| SQLGlot | `sqlglot>=30.19,<30.20` (Extra) | Keiner: `sqlglot_adapter.py` ist fest verdrahtet | Im Aufruf (`sqlglot_adapter.py:63`) | `lineage-sqlglot`, blockiert durch Vorschlag 0003 | Hostgrenze fehlt |
| Lokale Embeddings | `llama-cpp-python>=0.3.16,<0.4` (Extra) | `EmbeddingBackend`-Protocol, aber ohne Entry Point | Im Aufruf (`retrieval/local.py:215`) | `retrieval-llamacpp`, blockiert durch Vorschlag 0003 | Hostgrenze fehlt |
| Reranking | wie oben | Kein Protocol, fest verdrahtet | Im Aufruf (`retrieval/rerank.py:33`) | wie oben | Hostgrenze fehlt |
| Vectorranking | `sqlite-vec==0.1.9` (Extra) | Im Index fest verdrahtet | Im Aufruf (`retrieval/index.py:728`) | Bleibt im Host | – |
| BM25 | keine | Im Kern | – | Bleibt im Host | – |
| YAML-Semantik | `PyYAML>=6,<7` (Extra) | Im Kern | Im Aufruf (`semantics/structured.py:52`) | Bleibt im Host | – |

Die Host-Quellcodesuche findet genau zwei Entry-Point-Gruppen: `tarel.connectors` und
`tarel.providers`. Alles andere wäre eine erfundene Grenze.

## Befunde zum Connector-Vertrag

1. **Stilles Überschatten.** `load_manifest` prüft eingebaute Namen zuerst. Ein installiertes Paket
   mit dem Entry Point `sqlserver` wird ohne jede Meldung ignoriert. Ein Hub-Paket für SQL Server wäre
   heute wirkungslos und irreführend. Ein Test hält das fest, Vorschlag 0001 behebt es.
2. **Falscher Installationshinweis.** Bei fehlendem Treiber empfiehlt der Host auch externen Paketen
   `pip install tarel[extra]`. Auch das behebt Vorschlag 0001.
3. **Unvollständigkeit ist nicht ausdrückbar.** `CatalogResult` kennt weder Vollständigkeit noch
   Warnungen. Bei Oracle sieht ein entzogenes Recht deshalb wie eine Löschung aus, und der Sync gibt
   das weiter. Das ist die wichtigste offene Lücke, siehe Vorschlag 0002.
4. **`sample_rows` ohne Capability-Prüfung.** `sample_connector_use_case` ruft die Methode auf, obwohl
   die Vorlage von `connector scaffold` sie nicht anlegt. `profile_object` prüft dagegen. Der
   Oracle-Adapter fängt das mit einem eigenen klaren Fehler ab.
5. **Refresh gibt den Katalog als `database` zurück.** Oracle verwendet daher den konfigurierten
   Dienstnamen als stabilen Katalog.
6. **Gleiche Version, anderer Vertrag.** Der öffentliche `tarel 0.0.3` hat weder
   `tarel.connectors.catalog` noch `tarel.errors`, der lokale `0.0.3` schon. Ein Import von
   `validate_catalog_result` ließ den Adapter dort scheitern. Er nutzt jetzt nur noch
   `tarel.connectors.contracts`. Deshalb dokumentiert `docs/compatibility/` den Commit.

## Lizenzen aus den echten Artefakten

Gelesen aus den Wheels für cp312/manylinux am 04.11.2026. Das ist Evidenz für eine Prüfung, keine
Rechtsberatung.

### oracledb 26.1.0

`License-Expression: UPL-1.0 OR Apache-2.0`, mit `LICENSE.txt`, `NOTICE.txt` und
`THIRD_PARTY_LICENSES.txt` im Wheel. Vier eigene native Module, darunter `thick_impl`, das erst mit
`init_oracle_client` Oracle-Client-Bibliotheken braucht. Der Adapter ruft das nie auf, und im Wheel
sind keine Client-Bibliotheken enthalten. Der Thin-Modus verbindet laut Dokumentation zu Oracle
Database 12.1 oder neuer.

Der Hub gibt nichts davon weiter: `oracledb` kommt beim Nutzer aus dem konfigurierten Index.

### pymssql 2.4.6: offener Befund

- **Metadaten:** Das `License`-Feld enthält den LGPL-Text, und es gibt keine `License-Expression`.
- **FreeTDS:** Es liegt nicht als eigene Datei vor. `_mssql.so` enthält FreeTDS-Zeichenketten, ist
  also vermutlich statisch gelinkt. Eine eigene FreeTDS-Lizenzdatei fehlt.
- **Weitere gebündelte Bibliotheken in `pymssql.libs/`:** `libssl` und `libcrypto` **1.1.1k**,
  `libkrb5`, `libgssapi_krb5`, `libk5crypto`, `libkrb5support`, `libcom_err`, `libkeyutils`,
  `libpcre2-8`, `libselinux`. Das Wheel enthält dafür **nur den LGPL-Text**.
- **Sicherheit:** OpenSSL 1.1.1 ist laut OpenSSL-Projekt seit September 2023 außerhalb des
  regulären Supports. Das stammt aus meinem Wissen, die genaue Lage gehört vor einer Empfehlung
  geprüft.

**Folge:** Solange Nutzer `pymssql` selbst von PyPI beziehen, gibt der Hub das Wheel nicht weiter.
Sobald wir es in ein Offline-Bundle oder einen Container legen, verteilen wir diese Binärdateien
selbst und müssen die Pflichten aus LGPL und den übrigen Lizenzen erfüllen. Das ist vor einem solchen
Bundle zu klären. Für SQL Server wäre außerdem zu prüfen, ob ein anderer Treiber sinnvoller ist.

## Minimaler Kompatibilitäts- und Migrationsplan

1. **Nichts am Host brechen.** `tarel[sqlserver]`, `tarel[local-rag]`, `tarel[vector]` und
   `tarel[sql-lineage]` bleiben, wie sie sind.
2. **Neue Quellen zuerst extern.** Oracle ist der Beweis, dass ein unveränderter Host ein externes
   Paket laden und nutzen kann.
3. **SQL Server erst nach Vorschlag 0001** und einer Entscheidung: umziehen oder eingebaut lassen.
   Ein Umzug bräuchte einen Übergang für heutige Nutzer und vermeidet doppelte Implementierungen.
4. **Retrieval und SQLGlot erst nach Vorschlag 0003.** Bis dahin wäre jedes Paket nur ein Wrapper um
   private Hostfunktionen.
5. **Dokumente zuerst** über die vorhandenen Knowledge-Anwendungsfälle: Das geht ohne neuen Vertrag.
