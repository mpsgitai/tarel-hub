"""Local CPU Qwen3 embedding and reranking plugin for TAREL."""

from __future__ import annotations

import math
import os
import threading
from pathlib import Path
from threading import RLock
from typing import Any

from tarel.retrieval.contracts import ModelSpec, RetrievalFailure
from tarel.retrieval.local import (
    DEFAULT_MODEL_NAME,
    qwen_embedding_query,
    resolve_model_path,
)

EMBEDDING_TOKEN_CAPACITY = 2048
_LLAMA_PHYSICAL_BATCH = 256
LOCAL_EMBEDDING_INPUT = (
    f"llama.cpp:max_tokens={EMBEDDING_TOKEN_CAPACITY}:overflow=recorded_document_cut"
)

MODEL_SPECS: dict[str, ModelSpec] = {
    DEFAULT_MODEL_NAME: ModelSpec(
        name=DEFAULT_MODEL_NAME,
        filename="qwen3-embedding-0.6b-q4-k-m.gguf",
        url=(
            "https://huggingface.co/enacimie/"
            "Qwen3-Embedding-0.6B-Q4_K_M-GGUF/resolve/"
            "51fe2a65af23d8cfd3c9c1d89846cf9073f8902b/"
            "qwen3-embedding-0.6b-q4-k-m.gguf"
        ),
        sha256="17c3e3f2eaabc6e321702b4a13680d042e72afc5d602f359f27a670c3e54718c",
        size=396_474_560,
        source="https://huggingface.co/enacimie/Qwen3-Embedding-0.6B-Q4_K_M-GGUF",
        task="embedding",
    ),
    "qwen3-reranker-0.6b-q4-k-m": ModelSpec(
        name="qwen3-reranker-0.6b-q4-k-m",
        filename="Qwen3-Reranker-0.6B-q4_k_m.gguf",
        url=(
            "https://huggingface.co/Mungert/Qwen3-Reranker-0.6B-GGUF/resolve/"
            "041387f8ed7ead711b9496b153b682c5b2f5d158/Qwen3-Reranker-0.6B-q4_k_m.gguf"
        ),
        sha256="66867f47323e058f9dbfe24a13268859a84d9e9a8bb89ad0789c7c52131267e2",
        size=394_705_248,
        source="https://huggingface.co/Mungert/Qwen3-Reranker-0.6B-GGUF",
        task="reranker",
    ),
}

_RERANK_PREFIX = (
    "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query "
    'and the Instruct provided. Note that the answer can only be "yes" or "no".'
    "<|im_end|>\n<|im_start|>user\n"
)
_RERANK_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


class LlamaCppEmbeddingPlugin:
    """Entry-point plugin implementing TAREL's ``LocalEmbeddingPlugin`` protocol."""

    @property
    def name(self) -> str:
        return "llamacpp"

    @property
    def input_strategy(self) -> str:
        return LOCAL_EMBEDDING_INPUT

    @property
    def models(self) -> tuple[ModelSpec, ...]:
        return tuple(spec for spec in MODEL_SPECS.values() if spec.task == "embedding")

    def create_embedder(
        self,
        model_path: Path,
        *,
        n_threads: int | None = None,
    ) -> LlamaCppEmbedding:
        return LlamaCppEmbedding(model_path, n_threads=n_threads)


class LlamaCppRerankerPlugin:
    """Entry-point plugin implementing TAREL's ``LocalRerankerPlugin`` protocol."""

    @property
    def name(self) -> str:
        return "llamacpp"

    @property
    def models(self) -> tuple[ModelSpec, ...]:
        return tuple(spec for spec in MODEL_SPECS.values() if spec.task == "reranker")

    def create_reranker(
        self,
        model_path: Path,
        *,
        n_threads: int | None = None,
    ) -> LocalQwenReranker:
        return LocalQwenReranker(model_path, n_threads=n_threads)


def create_embedding_plugin() -> LlamaCppEmbeddingPlugin:
    return LlamaCppEmbeddingPlugin()


def create_reranker_plugin() -> LlamaCppRerankerPlugin:
    return LlamaCppRerankerPlugin()


class LlamaCppEmbedding:
    """CPU-only Qwen-compatible embeddings without LlamaIndex or a server."""

    def __init__(
        self,
        model_path: Path,
        *,
        n_threads: int | None = None,
    ) -> None:
        resolved = resolve_model_path(model_path)
        try:
            import llama_cpp
            from llama_cpp import Llama
        except ImportError as exc:
            raise RetrievalFailure(
                "missing_local_rag_dependency",
                "llama-cpp-python is not installed. "
                "Reinstall `tarel-retrieval-llamacpp` from TAREL Hub.",
            ) from exc
        threads = n_threads or max(1, (os.cpu_count() or 2) - 1)
        self._model_path = resolved
        version = getattr(llama_cpp, "__version__", "")
        self._runtime_version = f"llama-cpp-python {version}" if version else ""
        self._embedding_lock = threading.Lock()
        self._model: Any = Llama(
            model_path=str(resolved),
            n_ctx=EMBEDDING_TOKEN_CAPACITY,
            n_batch=EMBEDDING_TOKEN_CAPACITY,
            n_ubatch=_LLAMA_PHYSICAL_BATCH,
            n_threads=threads,
            n_gpu_layers=0,
            embedding=True,
            verbose=False,
        )

    @property
    def model_id(self) -> str:
        return self._model_path.name

    @property
    def input_strategy(self) -> str:
        return LOCAL_EMBEDDING_INPUT

    @property
    def max_input_tokens(self) -> int:
        return EMBEDDING_TOKEN_CAPACITY

    @property
    def runtime_version(self) -> str:
        return self._runtime_version

    def token_count(self, text: str) -> int:
        """Count tokens as ``embed`` will see them, including special tokens it adds."""
        with self._embedding_lock:
            return len(self._model.tokenize(text.encode("utf-8")))

    def embed_documents(
        self,
        texts: tuple[str, ...],
        *,
        batch_size: int,
    ) -> tuple[tuple[float, ...], ...]:
        if not 1 <= batch_size <= 256:
            raise RetrievalFailure("invalid_batch_size", "Batch size must be between 1 and 256.")
        vectors: list[tuple[float, ...]] = []
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset : offset + batch_size]
            for position, text in enumerate(batch, start=offset + 1):
                vectors.append(self._embed(text, f"Document {position} of {len(texts)}"))
        return tuple(vectors)

    def embed_query(self, text: str) -> tuple[float, ...]:
        return self._embed(qwen_embedding_query(text), "Query with its retrieval instruction")

    def embed_cut_document(self, text: str) -> tuple[float, ...]:
        """Embed only the first tokens of a text whose caller records that it was shortened."""
        try:
            with self._embedding_lock:
                embedded = self._model.embed(text, normalize=True, truncate=True)
        except Exception as exc:
            raise RetrievalFailure(
                "embedding_failed",
                "llama.cpp failed while embedding a shortened document.",
            ) from exc
        return _normalized_vector(embedded)

    def _embed(self, text: str, label: str) -> tuple[float, ...]:
        """Embed the whole text or refuse it; never let llama.cpp shorten it."""
        tokens = self.token_count(text)
        if tokens > EMBEDDING_TOKEN_CAPACITY:
            raise RetrievalFailure(
                "embedding_input_too_long",
                f"{label} has {tokens} tokens; the embedding limit is "
                f"{EMBEDDING_TOKEN_CAPACITY}. Nothing was shortened.",
            )
        try:
            with self._embedding_lock:
                embedded = self._model.embed(text, normalize=True, truncate=False)
        except Exception as exc:
            raise RetrievalFailure(
                "embedding_failed",
                f"llama.cpp failed while embedding: {label.lower()}.",
            ) from exc
        return _normalized_vector(embedded)


class LocalQwenReranker:
    """CPU-only Qwen3 reranker using llama.cpp yes/no logit scoring."""

    def __init__(self, path: Path, *, n_threads: int | None = None) -> None:
        try:
            from llama_cpp import Llama, llama_get_logits_ith
        except ImportError as exc:
            raise RetrievalFailure(
                "missing_local_rag_dependency",
                "llama-cpp-python is not installed. "
                "Reinstall `tarel-retrieval-llamacpp` from TAREL Hub.",
            ) from exc
        self.lock = RLock()
        self.next_logits = llama_get_logits_ith
        self.model = Llama(
            model_path=str(path),
            n_gpu_layers=0,
            n_ctx=4096,
            n_batch=256,
            n_threads=n_threads,
            logits_all=False,
            verbose=False,
        )
        labels = [self.model.tokenize(label.encode(), add_bos=False) for label in ("no", "yes")]
        if any(len(tokens) != 1 for tokens in labels):
            raise RetrievalFailure(
                "unsupported_reranker", "Qwen reranking needs single-token yes/no labels."
            )
        self.no, self.yes = (tokens[0] for tokens in labels)

    def score(self, query: str, texts: tuple[str, ...]) -> tuple[float, ...]:
        scores = []
        with self.lock:
            for text in texts:
                prefix = self.model.tokenize(
                    (
                        _RERANK_PREFIX
                        + "<Instruct>: Retrieve relevant database objects.\n"
                        + f"<Query>: {query}\n<Document>: "
                    ).encode(),
                    add_bos=True,
                    special=True,
                )
                suffix = self.model.tokenize(_RERANK_SUFFIX.encode(), add_bos=False, special=True)
                document = self.model.tokenize(text.encode(), add_bos=False)
                available = 4096 - len(prefix) - len(suffix)
                if available < 1:
                    raise RetrievalFailure(
                        "rerank_query_too_long", "Query exceeds the local rerank context."
                    )
                self.model.reset()
                self.model.eval(prefix + document[:available] + suffix)
                logits = self.next_logits(self.model.ctx, -1)
                if not logits:
                    raise RetrievalFailure("reranking_failed", "Local reranker omitted logits.")
                difference = float(logits[self.yes]) - float(logits[self.no])
                if not math.isfinite(difference):
                    raise RetrievalFailure(
                        "reranking_failed", "Local reranker returned invalid logits."
                    )
                scores.append(
                    1 / (1 + math.exp(-difference))
                    if difference >= 0
                    else math.exp(difference) / (1 + math.exp(difference))
                )
        return tuple(scores)


def _normalized_vector(value: object) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise RetrievalFailure("embedding_failed", "Embedding must be a non-empty number array.")
    try:
        vector = tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise RetrievalFailure("embedding_failed", "Embedding contains a non-number.") from exc
    if not all(math.isfinite(item) for item in vector):
        raise RetrievalFailure("embedding_failed", "Embedding contains a non-finite number.")
    magnitude = math.sqrt(sum(item * item for item in vector))
    if magnitude == 0:
        raise RetrievalFailure("embedding_failed", "Embedding has zero magnitude.")
    return tuple(item / magnitude for item in vector)
