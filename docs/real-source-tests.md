# Echte Quellen: Fixtures und Wiederholung

Stand 24.11.2026, Linux x86-64 (WSL2), Python 3.12, Host `tarel 0.0.5`. Jeder Connector hat eine
Fixture für einen **Wegwerf-Server** und einen Test, der nur mit gesetzter Variable läuft. Ohne
Variable wird er übersprungen. Die Fixtures legen eine Leserolle mit Teilrechten an; ein nicht
freigegebenes Objekt (`payroll`) muss unsichtbar bleiben.

| Paket | Server (Image) | Fixture | Variable | Leser-URL |
| --- | --- | --- | --- | --- |
| postgres | `postgres:17.7-bookworm` | `tests/fixture.sql` (psql als `postgres`) | `HUB_TEST_POSTGRES_URL` | `postgresql://hubtest_reader:hubtest-reader@127.0.0.1:55432/postgres` |
| oracle | `gvenzl/oracle-free:23-slim-faststart` | `tests/fixture.sql` (sqlplus als `SYSTEM` auf `FREEPDB1`) | `HUB_TEST_ORACLE_URL` | `oracle://hubtest_reader:hubtest-reader@127.0.0.1:51521/FREEPDB1` |
| mongodb | `mongo:8.0` | `tests/fixture.py ADMIN_URL` | `HUB_TEST_MONGODB_URL` | `mongodb://hubtest_lister:hubtest-lister@127.0.0.1:57017/hubtest` |
| mysql | `mysql:8.4` und `mariadb:11.4` | `tests/fixture.sql` (als `root`) | `HUB_TEST_MYSQL_URL`, `HUB_TEST_MARIADB_URL` | `mysql://hubtest_reader:hubtest-reader@127.0.0.1:53306/hubtest` (MariaDB: 53307) |
| clickhouse | `clickhouse/clickhouse-server:25.8` | `tests/fixture.sql` (als Admin, `--multiquery`) | `HUB_TEST_CLICKHOUSE_URL` | `clickhouse://hubtest_reader:hubtest-reader@127.0.0.1:58123/hubtest` |

Die Leserpasswörter sind absichtlich feste Fixture-Werte; Admin-Passwörter der Container werden
zufällig erzeugt und nie eingecheckt. Container nur an `127.0.0.1` binden und danach entfernen.

## Ergebnis vom 24.11.2026

- 113 Tests bestanden, keiner übersprungen, mit allen sechs Fixtures.
- Oracle Database 23ai Free 23.26.4: erster Lauf gegen eine echte Datenbank. Katalog, Kommentare,
  zusammengesetzter PK in Schlüsselreihenfolge, quotierte Namen, FKs, Sichtbarkeit nach Grants und
  `authentication_failed` bei falschem Passwort entsprechen den Mock-Annahmen.
- MariaDB zeigt `information_schema.TABLE_CONSTRAINTS` einer Rolle mit reinen Objektrechten nicht an.
  Der MySQL-Connector liest Schlüssel deshalb nur aus `KEY_COLUMN_USAGE`.
- PostgreSQL zusätzlich gegen lokale Server 17.7 und 16.3 mit einer Rolle `pg_read_all_data` und
  `default_transaction_read_only = on`: vier echte Datenbanken mit 14 bis 37 Objekten. libpq meldet
  Login-, Datenbank- und Netzfehler gleich und lokalisiert; der Connector unterscheidet daher nur
  `connection_failed` (Aufbau) und `source_failed` (Abfrage).
- CLI: `tarel graph build` und unveränderter `graph refresh` für postgres, mysql (MariaDB) und
  clickhouse aus frisch installierten Wheels.
- Alle zwölf Wheels und sdists bestehen `tools/check_distribution.py`; `tools/check_licenses.py` ohne
  Befund. Inventare für postgres, mysql und clickhouse liegen für linux-x86_64/py312 vor.

## Nutzerlauf vom 24.11.2026 (WSL2 und Windows)

Frische Umgebungen wie bei einem neuen Nutzer: `tarel` aus dem Branch `feat/connector-auth`, alle
sechs Hub-Pakete aus ihren sdists, dazu `pymssql` und `psycopg-binary`. Je Quelle `graph build`,
unveränderter `graph refresh`, `search --mode bm25` und `context build`.

| Umgebung | Quellen | Ergebnis |
| --- | --- | --- |
| Linux (WSL2), Python 3.12 | Kopien von drei BI-Lab-DuckDB-Dateien und zwei SQLite-Dateien (eine leer); PostgreSQL 17.7 (vier echte Datenbanken) und 16.3 | Graphen wie erwartet; Fremdschlüssel als `foreign_key`-Kanten; leere Quellen ergeben leere Graphen; unbekannte Datenbank: `connection_failed` |
| Linux (WSL2) | Synthetisches Schema mit 300 Tabellen, 7 799 Feldern, 299 FKs und Kommentaren in PostgreSQL, MySQL, MariaDB, Oracle, ClickHouse; MongoDB mit 300 Collections und 10 Views | Alle Zählungen exakt; Kommentare über die Suche auffindbar; Aufbau unter 1,5 s, Oracle 6,3 s |
| Windows 11, Python 3.12.10 | Dieselben Hub-Pakete gegen dieselben Server sowie DuckDB/SQLite-Kopien; SQL Server 2025 mit Windows-Auth über `auth = "integrated"` (acht Datenbanken, bis 100 Objekte) | Alle Graphen und Refreshes ok. Befund: `duckdb:///C:/…` wurde abgelehnt; behoben mit `url2pathname` |

Hub-Connectoren deklarieren noch kein `auth` im Manifest; eine `auth`-Konfiguration wird deshalb
klar mit `unsupported_auth` abgelehnt und das Login bleibt in der URL.

## Offen

- macOS ist ungeprüft; Windows nur mit Python 3.12.
- `auth` (Credential) für die Hub-Connectoren, sobald der Host-Vertrag released ist.
- TLS-Optionen für mysql fehlen; clickhouse kann `clickhouses://`, ungetestet.
- Kein Connector liest Zeilen oder Profile; nur `probe` und `discover_catalog`.
