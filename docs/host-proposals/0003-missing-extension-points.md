# Vorschlag 0003: Fehlende Erweiterungsgrenzen

**Status: zur Besprechung. Keine dieser Gruppen existiert, und der Hub gibt keine als unterstützt aus.**

Der Host kennt nur `tarel.connectors` und `tarel.providers`. Ein Hub-Paket für die folgenden
Fähigkeiten wäre heute ein Wrapper um private Funktionen, was der Auftrag ausschließt.

| Fähigkeit | Vorhanden | Fehlt |
| --- | --- | --- |
| Embeddings | `EmbeddingBackend`-Protocol in `retrieval/contracts.py` | Auswahl und Entry Point; `embedding_backend` erzeugt das lokale Backend fest |
| Reranking | Implementierung in `retrieval/rerank.py` | Protocol und Entry Point |
| SQL-Lineage | `sqlglot_adapter.py`, `lineage analyze --analyzer` | Analyzer-Protocol und Entry Point |
| Dokument-Importer | Knowledge-Anwendungsfälle | Nichts Neues nötig: Ein Importer kann sie direkt aufrufen |

## Zu entscheiden

Vor einem Entwurf sind drei Fragen offen:

1. Lohnt der Umzug von SQLGlot und llama.cpp überhaupt? Beide sind heute lazy und optional. Der
   Nutzer gewinnt wenig, solange sie im Host funktionieren, und zwei parallele Implementierungen sind
   ausdrücklich unerwünscht.
2. Wenn ja: Reicht je eine kleine Gruppe (`tarel.embeddings`, `tarel.rerankers`,
   `tarel.lineage_analyzers`) mit dem Muster der Connectoren? Das ist meine Empfehlung, ohne Framework.
3. Wie bleiben Index-Identität und Kompatibilität gewahrt, also Modellrevision, Hash und
   `input_strategy`, wenn das Backend von außen kommt?

Bis dahin bleiben `tarel[local-rag]` und `tarel[sql-lineage]` der gültige Weg, und der Katalog führt
beide nur als `planned`.
