# TAREL postgres

Liest Tabellen, Views, materialisierte Views, Fremdtabellen, Spalten, Kommentare, Primär- und
Fremdschlüssel aus `pg_catalog`, immer in einer Read-only-Transaktion mit 30 s Statement-Timeout.
Gemeldet werden nur Objekte, auf die die Anmeldung `SELECT` hat; Partitionen erscheinen über ihre
Elterntabelle. Zeilen werden nicht gelesen.

```sh
uv pip install --index-url https://pypi.org/simple "./packages/connector-postgres[binary]"
tarel connector check postgres
```

`[binary]` bringt libpq, OpenSSL und Kerberos als Wheel mit (`psycopg-binary`). Ohne das Extra nutzt
psycopg die libpq des Systems.

Die Konfiguration verwendet die Sektion `[postgres]` und den Schlüssel `url` oder die Variable
`TAREL_POSTGRES_URL`, z. B. `postgresql://reader@db.example:5432/dwh`. Fehlt das Passwort in der URL,
entscheidet libpq: `PGPASSFILE`/`pgpass`, SSPI, GSSAPI oder Peer-Anmeldung. Empfohlen ist eine eigene
Rolle mit `pg_read_all_data` oder gezielten `SELECT`-Rechten und
`default_transaction_read_only = on`.
