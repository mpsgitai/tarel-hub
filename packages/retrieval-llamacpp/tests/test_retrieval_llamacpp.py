"""Tests for the TAREL Hub local llama.cpp Qwen3 embedding & reranker plugin."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tarel_retrieval_llamacpp.plugin import (
    LOCAL_EMBEDDING_INPUT,
    MODEL_SPECS,
    LocalQwenReranker,
    create_embedding_plugin,
    create_reranker_plugin,
)


def test_plugins_declare_pinned_https_qwen_model_specs_without_bundling_weights() -> None:
    embedder = create_embedding_plugin()
    reranker = create_reranker_plugin()

    assert embedder.name == "llamacpp"
    assert embedder.input_strategy == LOCAL_EMBEDDING_INPUT
    assert reranker.name == "llamacpp"

    assert len(embedder.models) == 1
    assert embedder.models[0].name == "qwen3-embedding-0.6b-q4-k-m"
    assert embedder.models[0].url.startswith("https://huggingface.co/")
    assert len(embedder.models[0].sha256) == 64

    assert len(reranker.models) == 1
    assert reranker.models[0].name == "qwen3-reranker-0.6b-q4-k-m"
    assert reranker.models[0].url.startswith("https://huggingface.co/")
    assert len(reranker.models[0].sha256) == 64
    assert set(MODEL_SPECS) == {"qwen3-embedding-0.6b-q4-k-m", "qwen3-reranker-0.6b-q4-k-m"}


def test_local_qwen_reranker_reads_final_native_logits_and_bounds_long_documents() -> None:
    class FakeLlama:
        ctx = object()

        def __init__(self, **kwargs):
            self.arguments = kwargs
            self.evaluations = []

        def tokenize(self, value, **kwargs):
            if value == b"no":
                return [0]
            if value == b"yes":
                return [1]
            return [2] * len(value)

        def reset(self):
            pass

        def eval(self, tokens):
            self.evaluations.append(tokens)

        @property
        def scores(self):
            raise AssertionError("The unused Python scores buffer must not be read.")

    calls = []

    def logits(context, row):
        calls.append((context, row))
        return [0.0, 2.0]

    module = SimpleNamespace(Llama=FakeLlama, llama_get_logits_ith=logits)
    with patch.dict("sys.modules", {"llama_cpp": module}):
        ranker = LocalQwenReranker(Path("model.gguf"), n_threads=4)
        scores = ranker.score("revenue", ("x" * 10_000,))
    assert scores[0] > 0.8
    assert calls == [(ranker.model.ctx, -1)]
    assert len(ranker.model.evaluations[0]) == 4096
    assert ranker.model.arguments["logits_all"] is False
    assert ranker.model.arguments["n_gpu_layers"] == 0
