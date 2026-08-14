"""Embedding.

**English-only on purpose.** The corpus is English and DeepSeek translates an Urdu question
into English before retrieval, so the embedder never sees Urdu. That frees us to use the
strongest English retriever at this size rather than paying the quality tax a multilingual
model charges for languages we no longer route through it.

The trade is explicit: translation adds a step where a mistranslated symptom could retrieve
the wrong disease. That step is logged (see ``retrieve.translate_query``) so a bad answer can
be traced to a bad translation instead of being blamed on retrieval.

``all-mpnet-base-v2`` is ~420 MB and 768-dimensional -- a fifth of BGE-M3's size, and it runs
comfortably on a laptop CPU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

#: Strong English retrieval, small enough for CPU. Queries arrive pre-translated.
DEFAULT_MODEL = "sentence-transformers/all-mpnet-base-v2"

#: Multilingual fallback, kept for the case where translation-before-retrieval is
#: abandoned and the embedder has to handle Urdu directly again.
FALLBACK_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

DENSE_DIM = 768  # all-mpnet-base-v2


@dataclass(slots=True)
class EmbeddingBatch:
    """Dense vectors, and sparse ones when the model produces them."""

    dense: np.ndarray
    sparse: list[dict[int, float]] | None = None

    def __len__(self) -> int:
        return len(self.dense)


class Embedder:
    """Wraps BGE-M3, falling back to a dense-only model when it is unavailable.

    The model is loaded lazily: importing this module must stay cheap, because the CLI
    imports it to print help text long before anyone embeds anything.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        use_fp16: bool = False,
        batch_size: int = 8,
    ) -> None:
        self.model_name = model_name
        self.use_fp16 = use_fp16  # fp16 on CPU is slower, so this stays off by default
        self.batch_size = batch_size
        self._model: Any = None
        self._is_m3 = False

    def load(self) -> None:
        if self._model is not None:
            return

        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(self.model_name, use_fp16=self.use_fp16)
            self._is_m3 = True
            return
        except Exception:
            pass  # fall through to the dense-only path

        from sentence_transformers import SentenceTransformer

        name = self.model_name
        self._model = SentenceTransformer(name)
        self.model_name = name
        self._is_m3 = False

    @property
    def produces_sparse(self) -> bool:
        return self._is_m3

    @property
    def dimension(self) -> int:
        self.load()
        if self._is_m3:
            return DENSE_DIM
        return int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str], *, show_progress: bool = False) -> EmbeddingBatch:
        """Embed a list of texts."""
        self.load()

        if self._is_m3:
            output = self._model.encode(
                texts,
                batch_size=self.batch_size,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )
            dense = np.asarray(output["dense_vecs"], dtype=np.float32)
            sparse = [
                {int(token): float(weight) for token, weight in entry.items()}
                for entry in output["lexical_weights"]
            ]
            return EmbeddingBatch(dense=dense, sparse=sparse)

        dense = np.asarray(
            self._model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=True,
            ),
            dtype=np.float32,
        )
        return EmbeddingBatch(dense=dense)

    def encode_query(self, text: str) -> EmbeddingBatch:
        return self.encode([text])


def bm25_sparse(
    texts: list[str], vocabulary: dict[str, int] | None = None
) -> tuple[list[dict[int, float]], dict[str, int]]:
    """A BM25-style sparse fallback for when the model has no sparse head.

    Not as good as BGE-M3's learned sparse weights, but it preserves the property that
    matters: exact terms like ``TR4`` stay findable when a dense vector would smear them
    into general fungicide language.
    """
    import math
    import re
    from collections import Counter

    tokenise = re.compile(r"[a-z0-9]+").findall
    documents = [tokenise(text.lower()) for text in texts]

    vocab = dict(vocabulary or {})
    if not vocab:
        for tokens in documents:
            for token in tokens:
                vocab.setdefault(token, len(vocab))

    frequency = Counter(token for tokens in documents for token in set(tokens))
    total = max(len(documents), 1)
    average_length = sum(len(t) for t in documents) / total or 1.0

    k1, b = 1.5, 0.75
    vectors: list[dict[int, float]] = []
    for tokens in documents:
        counts = Counter(tokens)
        length = len(tokens) or 1
        vector: dict[int, float] = {}
        for token, count in counts.items():
            index = vocab.get(token)
            if index is None:
                continue
            idf = math.log(1 + (total - frequency[token] + 0.5) / (frequency[token] + 0.5))
            norm = count * (k1 + 1) / (count + k1 * (1 - b + b * length / average_length))
            vector[index] = idf * norm
        vectors.append(vector)

    return vectors, vocab
