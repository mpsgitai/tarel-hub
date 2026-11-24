# Dependency- und Lizenzregeln

Die verbindlichen Regeln stehen in `OPUS_IMPLEMENTATION_PROMPT.md`, Abschnitt 5. Hier steht, wie sie
geprüft werden und was die Prüfung nicht leistet.

| Regel | Prüfung | Grenze |
| --- | --- | --- |
| Nichts Fremdes in Artefakten | `tools/check_distribution.py` liest Inhalte: ELF, Mach-O, PE, GGUF, SQLite, verschachtelte Archive, NUL-Bytes, Kopien bekannter Pakete, Vendor-Ordner | Eine bewusst getarnte Textkopie fremden Codes erkennt sie nicht |
| Dateitypen | Allowlist je Dateiendung | Allowlist, keine Inhaltsgarantie |
| Keine Secrets, privaten Pfade | Muster für Schlüssel, Tokens, Passwort-URLs, lokale Pfade | Muster finden nicht jedes Secret; Platzhalter wie `PASSWORD` sind erlaubt |
| Obergrenzen je Dependency | Prüfung der `Requires-Dist`-Zeilen | Sagt nichts über Sicherheit einer Version |
| Lizenz, Notices im Artefakt | Pflichtdateien in Wheel und sdist | Prüft Vorhandensein, nicht Richtigkeit |
| Dependency-Änderung braucht Lizenzprüfung | `tools/check_licenses.py` vergleicht `pyproject.toml`, `licenses.toml` und die Notices | Die Einträge pflegt ein Mensch |
| Tatsächlicher Bestand | `dependency-inventory.<plattform>.json` aus einer frischen Umgebung | Gilt für eine Plattform; Lizenzangaben stammen aus Paketmetadaten |
| Entry Point passt zum Manifest | `tools/check_distribution.py` | – |
| Eigene Lizenz (MIT) oder Upload-Sperre | Ein Wheel braucht eine eigene `LICENSE` oder `Private :: Do Not Upload`; heute tragen die Pakete beides | Ein Index lehnt ein gesperrtes Paket ab, lokal bleibt es installierbar |

Ein bestandener Lauf ist Evidenz für eine Prüfung, keine Rechtsgarantie.

## Bezug

Fremdbibliotheken kommen vom offiziellen Index oder einem freigegebenen internen Mirror. Weil unsere
Paketnamen nicht reserviert sind, gilt bei privaten Indizes: Index eindeutig festlegen, damit ein
gleichnamiges öffentliches Paket nicht gewinnt. Ein Offline-Bundle oder Container wäre eine eigene
Weiterverteilung und braucht eine eigene Freigabe mit vollständiger Lizenzprüfung.

## Ausnahmen

Keine ohne ausdrückliche Freigabe des Maintainers und ein Entscheidungsdokument mit Grund,
Komponente, Version und Hash, Lizenzpflichten, Lieferumfang, Updateverantwortung und Entfernungspfad.
Bisher gibt es keine Ausnahme.
