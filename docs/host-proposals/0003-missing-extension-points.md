# Vorschlag 0003: Erweiterungsgrenzen für Lineage-Analyzer und lokales Retrieval

**Status: umgesetzt (2026-11-25).**

Der Host stellt jetzt drei schlanke Entry-Point-Gruppen ohne Framework bereit:

| Fähigkeit | Entry-Point-Gruppe | Hub-Paket |
| --- | --- | --- |
| SQL-Lineage | `tarel.lineage_analyzers` (`sqlglot`) | `packages/lineage-sqlglot` (`tarel-lineage-sqlglot`) |
| Lokale Embeddings | `tarel.embeddings` (`llamacpp`) | `packages/retrieval-llamacpp` (`tarel-retrieval-llamacpp`) |
| Lokales Reranking | `tarel.rerankers` (`llamacpp`) | `packages/retrieval-llamacpp` (`tarel-retrieval-llamacpp`) |

Die früheren Host-Extras `tarel[sql-lineage]` und `tarel[local-rag]` sowie `sqlglot_adapter.py`, `LlamaCppEmbedding`, `LocalQwenReranker` und die fest eingebauten HuggingFace-Modell-URLs wurden aus dem Host entfernt. Modelle werden ausschließlich als gepinnte, SHA-256-verifizierte HTTPS-Links im Hub-Plugin deklariert und explizit vom Nutzer heruntergeladen.
