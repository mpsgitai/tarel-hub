"""TAREL Hub local embedding and reranking plugin backed by llama.cpp and Qwen3."""

from tarel_retrieval_llamacpp.plugin import (
    EMBEDDING_TOKEN_CAPACITY,
    LOCAL_EMBEDDING_INPUT,
    MODEL_SPECS,
    LlamaCppEmbedding,
    LlamaCppEmbeddingPlugin,
    LlamaCppRerankerPlugin,
    LocalQwenReranker,
    create_embedding_plugin,
    create_reranker_plugin,
)

__all__ = [
    "EMBEDDING_TOKEN_CAPACITY",
    "LOCAL_EMBEDDING_INPUT",
    "MODEL_SPECS",
    "LlamaCppEmbedding",
    "LlamaCppEmbeddingPlugin",
    "LlamaCppRerankerPlugin",
    "LocalQwenReranker",
    "create_embedding_plugin",
    "create_reranker_plugin",
]
