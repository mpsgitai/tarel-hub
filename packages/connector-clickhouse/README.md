# TAREL clickhouse

Liest Tabellen, Views, materialisierte Views, Spalten und Kommentare einer ClickHouse-Datenbank aus
`system.tables` und `system.columns`, über HTTP mit `readonly=1` und 30 s Ausführungslimit. Gezeigt
wird nur, was die Anmeldung sehen darf. Zeilen werden nicht gelesen. Geprüft mit ClickHouse 25.8.

Der ClickHouse-Primärschlüssel ist ein Sortierschlüssel ohne Eindeutigkeit. Er wird deshalb nicht als
Primärschlüssel gemeldet. ClickHouse kennt keine Fremdschlüssel.

```sh
uv pip install --index-url https://pypi.org/simple ./packages/connector-clickhouse
tarel connector check clickhouse
```

Die Konfiguration verwendet die Sektion `[clickhouse]` und den Schlüssel `url` oder die Variable
`TAREL_CLICKHOUSE_URL`, z. B. `clickhouse://reader:PASSWORD@db.example:8123/dwh` oder
`clickhouses://…:8443/dwh` für HTTPS.
