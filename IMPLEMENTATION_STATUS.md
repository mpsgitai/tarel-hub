# Implementierungsstand

Stand 05.11.2026 für DuckDB, MongoDB und die Prüfung der Vertrauensgrenzen: [Hub-Review](docs/hub-review.md). Die folgenden Oracle-Angaben dokumentieren den früheren Stand.
Stand 04.11.2026, Lieferschritte 1 bis 3 von 6. Host: `../TAREL_REFACTOR` auf `eeb559f`, sauber.
Einzelergebnisse stehen in [docs/compatibility/connector-oracle.json](docs/compatibility/connector-oracle.json).

**Kein Paket ist freigegeben oder veröffentlicht. Der Connector lief nie gegen eine echte Oracle-Datenbank.**

## Implementiert und getestet

| Baustein | Evidenz | Art |
| --- | --- | --- |
| `tarel-connector-oracle` lädt über Entry Point im unveränderten Host | Lokaler Host `eeb559f` und öffentlicher `tarel 0.0.3` | Echt, frische Umgebung außerhalb des Repos |
| Erkennung lädt keinen Treiber, funktioniert ohne Netz | `sys.modules`-Prüfung; `unshare -rn` | Echt |
| Nur das gewählte Paket: andere Treiber fehlen | `find_spec` für pymssql, llama_cpp, sqlglot, sqlite_vec, yaml, torch | Echt |
| Host allein bleibt ohne Treiber nutzbar | Eigene frische Umgebung | Echt |
| Echter Treiber, geschlossener Port: `connection_failed`, kein Secret | `oracledb` 26.1.0 mit echten Sockets | Echter Treiber, keine Datenbank |
| Abbildung von Objekten, Typen, PK, FK, Kommentaren, quotierten Namen | 48 Paket-Tests | **Mock**: geskripteter Treiber |
| Fehlerkategorien, keine Secrets, Verbindung wird immer freigegeben | Paket-Tests | **Mock** |
| Erster Graph und Refresh über die echte CLI | `verify_install` mit beiden Hosts | **Mock-Treiber**, echter Host |
| CLI und SDK: gleicher Graph, gleiche Fehlercodes | `test_host_path.py` | **Mock-Treiber**, echter Host |
| Doppelte Namen, falscher Vertrag, Schreibrecht, fehlender Treiber | `contract-tests/test_host_loading.py` | Echt, unveränderter Host |
| Distributionsprüfung erkennt Fremdinhalte, auch getarnt | `contract-tests/test_repository_rules.py` | Echt |
| Lizenzprüfung bricht bei geänderter Dependency | ebenda | Echt |
| Katalog auflisten importiert kein Plugin | ebenda | Echt |
| Wheel und sdist bauen und bestehen die Regeln | `verify_install` | Echt |

## Blockiert

| Punkt | Grund | Was es braucht |
| --- | --- | --- |
| Oracle gegen echte Datenbank | Keine autorisierte Instanz | Eine Testinstanz: **eine echte Datenbank kann SQL und Rechteverhalten anders zeigen als der Mock** |
| SQL Server als Hub-Paket | Der Host überschattet den Namen still | Entscheidung zu [Vorschlag 0001](docs/host-proposals/0001-connector-name-collision.md) |
| SQLGlot, Embeddings, Reranking als Pakete | Keine Host-Grenze | Entscheidung zu [Vorschlag 0003](docs/host-proposals/0003-missing-extension-points.md) |
| Entzogenes Recht von Löschung unterscheiden | Vertrag kann es nicht ausdrücken | Entscheidung zu [Vorschlag 0002](docs/host-proposals/0002-observation-completeness.md) |
| Veröffentlichung | Eigene Lizenz und Rechteinhaber offen | Entscheidung des Maintainers |

Vorschlag 0001 ist auf einer Wegwerf-Kopie von `eeb559f` geprüft: Der Patch lässt sich anwenden, ein
Namenskonflikt ergibt `ambiguous_connector`, und die 22 Connector-Tests des Hosts bestehen. Die
restliche Host-Suite lief dafür nicht. Der Host selbst blieb unverändert.

## Geplant

- Schritt 4: Dokumentimporter über die vorhandenen Knowledge-Anwendungsfälle.
- Schritt 5: SQLGlot und Embeddings, sobald Vorschlag 0003 entschieden ist.
- Schritt 6: Nutzerdokumentation und Gesamtbericht.

## Offene Befunde

- **Eigene Lizenz** nicht entschieden: `Private :: Do Not Upload` schützt vor Veröffentlichung.
- **pymssql 2.4.6** bündelt OpenSSL 1.1.1k, Kerberos und weitere Bibliotheken, liefert aber nur den
  LGPL-Text mit. Ein eigenes Offline-Bundle wäre davon direkt betroffen, siehe
  [docs/inventory.md](docs/inventory.md).
- **Inventar** liegt nur für linux-x86_64 und Python 3.12 vor. Windows und macOS sind ungeprüft.
- **Oracle-Abfragen** sind gegen die Dokumentation geschrieben. Performance auf großen Katalogen ist
  unbekannt, und es gibt keine Zeilenobergrenze.

## Tatsächliche Dependencies von `tarel-connector-oracle`

Aufgelöst am 04.11.2026 für linux-x86_64, Python 3.12, aus
[dependency-inventory.linux-x86_64-py312.json](packages/connector-oracle/dependency-inventory.linux-x86_64-py312.json):

| Paket | Version | Lizenz laut Metadaten | Native Dateien |
| --- | --- | --- | --- |
| oracledb | 26.1.0 | UPL-1.0 OR Apache-2.0 | 4 |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | 1 |
| cffi | 2.1.1 | MIT-0 | 1 |
| pycparser | 3.12 | BSD-3-Clause | 0 |
| typing_extensions | 4.16.0 | PSF-2.0 | 0 |
| tarel | 0.0.3 | MIT | 0 |

## Prüfungen wiederholen

```bash
uv venv .venv --python 3.12
uv build ../TAREL_REFACTOR --wheel --out-dir /tmp/host
uv pip install --python .venv/bin/python -r requirements-dev.txt /tmp/host/*.whl
uv pip install --python .venv/bin/python -e packages/connector-oracle
.venv/bin/python -m pytest
.venv/bin/python tools/verify_install.py connector-oracle --public-host 0.0.3
```
