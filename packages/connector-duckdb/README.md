# TAREL duckdb

Lokale, vorhandene DuckDB-Datei. Übergib einen absoluten Dateipfad oder duckdb:///absoluter/pfad.duckdb. Liest Tabellen, Views, Spalten und Primärschlüssel im ausgewählten Schema. Verwende nur vertrauenswürdige Dateien.

Aus dem Hub im eigenen TAREL-Environment installieren:

```sh
uv pip install --index-url https://pypi.org/simple ./packages/connector-duckdb
tarel connector check duckdb
```

Die Konfiguration verwendet die Sektion [duckdb] und den Schlüssel url oder die Variable TAREL_DUCKDB_URL. Probe und Katalogaufbau öffnen die Quelle.
