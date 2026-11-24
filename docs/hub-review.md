# Lokaler Hub-Review vom 05.11.2026

Der lokale Hub eignet sich als Katalog und als Installationsquelle für geprüfte eigene Pakete. Der Katalog liest TOML. Installierte Python-Plugins laufen mit den Rechten des Benutzers. Für beliebige Community-Beiträge braucht es vor der Installation eine Prüfung von Code, Build-Backend und aufgelösten Dependencies.

## Reproduzierte Sicherheitsbefunde

- **Host-Ladeweg**. Beim Aufruf von `tarel connector check` sucht der Host das punktierte Entry-Point-Modul mit `find_spec`. Dabei lief das Elternpaket eines synthetischen Testplugins und gab seinen Marker aus, bevor der Host das Manifest geprüft hat. Ein `permissions = ["read"]` im Manifest begrenzt Python-Code nicht. Vorschlag für den Host-Walkthrough: Manifest über die installierten Distributionsdateien lesen und Modulimport bis zur ausdrücklichen Nutzung vermeiden. Für nicht vertrauenswürdigen Code braucht es zusätzlich eine Prozessgrenze mit eingeschränkten Rechten.
- **Hub-Prüfwerkzeuge**. Die Katalogvalidierung begrenzt den aufgelösten Paketpfad jetzt auf direkte Kinder von `packages/`. Der Wheel-Check liest einzelne ZIP-Einträge anhand ihres Eintragsobjekts, meldet doppelte Pfade und ZIP-Symlinks. Vorher konnte ein späterer gleichnamiger Eintrag einen früheren Inhalt im Scan verdecken. Die Fremdpaketprüfung kennt nun auch die neuen Treibernamen. Der bestehende Installationsprüfer akzeptiert nur Oracle, dessen Szenarien er tatsächlich prüft.
- **Restgrenzen**. Der Archivprüfer hält entpackte Inhalte im Speicher und hat kein Größenbudget. Nur auf eigene lokal gebaute Artefakte anwenden. Die Prüfung authentifiziert weder Herausgeber noch Code. Die Vollständigkeit eines Katalog-Snapshots lässt sich im aktuellen Hostvertrag nicht kennzeichnen. Vor automatischen Refreshs Scope und Sichtrechte stabil halten.
- **Treiberprüfung**. pip-audit meldete für die drei aufgelösten neuen Drittkomponenten und die externen Python-Pakete des vorhandenen Oracle-Inventars keine bekannten Schwachstellen. Geltungsbereich sind diese Paketversionen und die beim Lauf verfügbaren Advisories. Native Bibliotheken, Datenbankserver und Betriebssystem sind gesondert zu prüfen.

## Funktionsnachweis

Linux x86-64, Python 3.12, lokaler Host-Checkout mit HEAD eeb559f und vorhandenen Arbeitsänderungen. Die beiden Adapter sind eigenständiger Hub-Code. Der lokale DuckDB-Lab-Connector und der Mongo-Leser waren fachliche Referenzen. Der Lab-Leser ermittelt Feldtypen aus Dokumentinhalten. Der Hub fragt ausschließlich Namen und Objekttypen über listCollections ab.

| Geprüfter Pfad | Beobachtung |
| --- | --- |
| Wheel und sdist beider Pakete | gebaut, Inhaltsprüfung bestanden, Wheel beim Echttest installiert, sdists in getrennten frischen Umgebungen installiert und vom Host gefunden |
| DuckDB 2.0.0 | temporäre echte Datenbank, Tabelle und View im Graph, Spalten, zusammengesetzter PK in Schlüsselreihenfolge, Schemafilter, unveränderte Datei. Der Connector öffnet nur existierende lokale Dateien read-only, mit externem Zugriff und automatischem Extension-Bezug deaktiviert. Fremdschlüssel werden in dieser Version nicht erfasst. |
| MongoDB 8.2.1 und PyMongo 4.19.0 | temporärer Container aus lokalem Image, synthetisches Dokument und View. Ein Nutzer nur mit listCollections konnte beide Objekte erfassen. find scheiterte mit MongoDB-Code 13. Der Nutzer ohne Katalogrecht erhielt beim Refresh einen bereinigten Fehler. Weder URI noch Testwert im Graph. |
| CLI und SDK | Probe, Graphaufbau und unveränderter Refresh über die CLI. SDK-Graphen beider Quellen hatten dieselben Knoten und Kanten, SDK-Refresh unverändert. |
| Wiederholbare Tests | 97 Tests mit installierten Paketen und Mongo-Testfixture. Für den optionalen Mongo-Test eine isolierte Datenbank hubtest mit Collection orders und View orderView bereitstellen und HUB_TEST_MONGODB_URL setzen. Ohne Fixture wird dieser Fall übersprungen. |

Oracle hat weiterhin nur Mock-Evidenz für einen erfolgreichen Katalogzugriff. SQL Server ist ein eingebauter Host-Connector. Windows, macOS und andere Hoststände sind für die beiden neuen Pakete offen.

## Treiberbezug und Veröffentlichung

Das Hub-Paket enthält den eigenen Adapter, das Manifest und Notices. Nur die Installation des jeweiligen Pakets löst die festgelegte Treiberversion über den gewählten Index auf. Für lokale Nutzung den geprüften TAREL-Host zuerst installieren. Einen einzigen offiziellen PyPI-Index oder einen intern freigegebenen Mirror verwenden. Für wiederholbare Deployments den kompletten plattformspezifischen Satz einschließlich transitiver Pakete mit Hashes fixieren. Die Inventare beschreiben den getesteten Stand.

- DuckDB 2.0.0 trägt MIT. Das Python-Wheel enthält zusätzlich eine Apache-2.0-Lizenz unter duckdb/experimental/spark/LICENSE. [Anbieterpaket](https://pypi.org/project/duckdb/2.0.0/)
- PyMongo 4.19.0 trägt Apache-2.0, seine hier aufgelöste Abhängigkeit dnspython 2.9.2 ISC. Der MongoDB-Server wird durch das Paket weder installiert noch verteilt. [Anbieterpaket](https://pypi.org/project/pymongo/4.19.0/)
- Eigene Lizenz: MIT (MPS), je Paket eine `LICENSE`. Bis zur PyPI-Entscheidung bleibt der private PyPI-Klassifikator. Offline-Wheelhouse oder Container separat nach tatsächlichem Lieferumfang und Notices beurteilen.
