# Host & Extension Inventory

Reference host: `tarel>=0.0.6,<0.1` (`mpsgitai/tarel`).

## Extension Boundaries

| Capability | Entry-Point Group | Host vs. Hub |
| --- | --- | --- |
| Source connectors | `tarel.connectors` | Built-in: `sqlite`, `sqlserver`. Hub: `duckdb`, `postgres`, `mysql`, `clickhouse`, `oracle`, `mongodb`. |
| LLM providers | `tarel.providers` | Built-in OpenAI-compatible / OpenRouter adapters in host; custom providers via entry point. |
| Static SQL lineage | `tarel.lineage_analyzers` | Hub only: `packages/lineage-sqlglot` (`sqlglot>=30.19,<30.20`, MIT). |
| Local embeddings | `tarel.embeddings` | Hub only: `packages/retrieval-llamacpp` (`llama-cpp-python>=0.3.16,<0.4`, MIT; Qwen3 links Apache-2.0). |
| Local reranking | `tarel.rerankers` | Hub only: `packages/retrieval-llamacpp`. |
| BM25 / sqlite-vec / YAML semantics | Built into host | Remain in `tarel`. |

## License Notes

- All adapter code in this repository is **MIT** (Copyright MPS).
- Third-party drivers and runtimes are installed directly from PyPI by the user and are never bundled in hub wheels or sdists.
- Note on host built-in `tarel[sqlserver]`: `pymssql` (LGPL-2.1) bundles native libraries inside its upstream wheel; avoid redistributing that wheel without a separate license review.
