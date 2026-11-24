# TAREL mysql

Liest Tabellen, Views, Spalten, Kommentare, Primär- und Fremdschlüssel eines MySQL- oder
MariaDB-Schemas aus `information_schema`, in einer `READ ONLY`-Transaktion mit 30 s Lese-Timeout.
`information_schema` zeigt nur Objekte, auf die die Anmeldung ein Recht hat. Zeilen werden nicht
gelesen. Geprüft mit MySQL 8.4 und MariaDB 11.4.

```sh
uv pip install --index-url https://pypi.org/simple ./packages/connector-mysql
tarel connector check mysql
```

Die Konfiguration verwendet die Sektion `[mysql]` und den Schlüssel `url` oder die Variable
`TAREL_MYSQL_URL`, z. B. `mysql://reader:PASSWORD@db.example:3306/dwh`. In MySQL ist Schema und
Datenbank dasselbe: `--database` wählt das Schema, `--namespace` muss dazu passen. Die Verbindung ist
unverschlüsselt; TLS ist noch nicht konfigurierbar.
