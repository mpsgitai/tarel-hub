# TAREL retrieval-llamacpp

Local CPU embeddings (`Qwen3-Embedding-0.6B`) and local reranking (`Qwen3-Reranker-0.6B`) for TAREL via `llama-cpp-python` and the `tarel.embeddings` / `tarel.rerankers` entry points (requires `tarel>=0.0.6`).

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/retrieval-llamacpp"
tarel model download
```

This package contains **no model weights** and **no bundled binaries**. It declares `llama-cpp-python` as an external dependency and references pinned, SHA-256-verified HuggingFace URLs (Apache-2.0); models are downloaded only when you explicitly run `tarel model download`.
