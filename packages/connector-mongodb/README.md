# TAREL mongodb

Gib die Datenbank im mongodb://-URI oder als database an. Der Nutzer benötigt listCollections auf dieser Datenbank. Collections und Zeitreihen erscheinen als Tabellen, Views als Views. Felder bleiben unbekannt. Keine Dokumentabfragen. Erlaubte URI-Optionen sind authSource, replicaSet und tls=true. Für entfernte Verbindungen TLS aktivieren.

Aus dem Hub im eigenen TAREL-Environment installieren:

```sh
uv pip install --index-url https://pypi.org/simple ./packages/connector-mongodb
tarel connector check mongodb
```

Die Konfiguration verwendet die Sektion [mongodb] und den Schlüssel url oder die Variable TAREL_MONGODB_URL. Probe und Katalogaufbau öffnen die Quelle.
