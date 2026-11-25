# TAREL retrieval-llamacpp

Lokale CPU-Embeddings (`Qwen3-Embedding-0.6B`) und lokales Reranking (`Qwen3-Reranker-0.6B`) für TAREL über `llama-cpp-python` und die Entry Points `tarel.embeddings` und `tarel.rerankers`.

Aus dem Hub im eigenen TAREL-Environment installieren:

```sh
uv pip install --index-url https://pypi.org/simple ./packages/retrieval-llamacpp
tarel model download
```

Dieses Paket enthält **keine Modellgewichte** und keine gebündelten Binärdateien. Es verlinkt lediglich gepinnte, SHA-256-geprüfte HuggingFace-Quellen (Apache-2.0); der Download erfolgt erst nach explizitem Aufruf von `tarel model download`.
