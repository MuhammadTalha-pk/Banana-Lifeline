"""Retrieval.

The pipeline, in order:

1. **Metadata pre-filter** on the disease the CNN already identified. This is the structural
   advantage over generic RAG — most systems must infer the topic from the question; this one
   was handed it by the classifier before the user typed anything.
2. **Hybrid search** — dense for meaning, sparse for exact terms.
3. **Reciprocal rank fusion** to merge the two rankings without needing their scores to be
   comparable, which they are not.
4. **Cross-encoder reranking** over the survivors.
5. **Authority and region preference** as the final tie-break.

Filtering is *preferred*, never absolute. A too-narrow filter that returns nothing is worse
than a broad search that returns something imperfect, so every filter falls back rather than
answering from an empty set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from banana_lifeline.rag.embed import Embedder
from banana_lifeline.rag.index import COLLECTION_NAME, _client

#: RRF damping. 60 is the value from the original paper and behaves well without tuning.
RRF_K = 60

#: Cross-encoder score below which the corpus is treated as unable to answer.
#:
#: Measured on the golden set, not guessed. Answerable questions score -3.1 to +7.5;
#: unanswerable ones -10.8 to -1.9. -3.5 sits below every answerable question, so it refuses
#: 4 of 5 unanswerable questions while losing none of the real ones.
#:
#: This works where cosine similarity did not because a cross-encoder reads the question and
#: passage together. Cosine only knows "banana price" and "banana disease" are both about
#: bananas; the cross-encoder knows one passage does not answer the other question.
MIN_RERANK_SCORE = -3.5

#: Minimum cosine similarity for the corpus to be considered capable of answering.
#:
#: Chosen by measuring the golden set rather than picked: answerable questions score
#: 0.38-0.73 (mean 0.60), unanswerable ones 0.30-0.54 (mean 0.42). The distributions
#: OVERLAP, so no threshold separates them cleanly -- 0.50 keeps ~83% of answerable
#: questions while refusing ~80% of unanswerable ones. The residual failures are
#: agricultural questions about the wrong crop or species, which are genuinely close to
#: this corpus in embedding space; a cross-encoder reranker is the fix, not a higher
#: threshold, which would start refusing real questions.
MIN_RELEVANCE = 0.50

_AUTHORITY_BONUS = {
    "international": 0.06,
    "scientific": 0.04,
    "university": 0.02,
    "national": 0.03,
}


@dataclass(slots=True)
class Retrieved:
    """One retrieved passage with its provenance and score."""

    chunk_id: str
    text: str
    context_prefix: str
    score: float
    source: str
    title: str
    url: str
    disease: str
    topic: str
    region: str
    authority: str
    heading_path: list[str] = field(default_factory=list)

    def citation(self) -> str:
        section = " > ".join(self.heading_path[-2:]) if self.heading_path else ""
        return f"{self.source} — {self.title}" + (f" ({section})" if section else "")


@dataclass(slots=True)
class RetrievalResult:
    """What retrieval found, and how it had to get there."""

    passages: list[Retrieved]
    #: Best raw cosine similarity. Used for the can-we-answer decision only when reranking
    #: is off: RRF is rank-based, so its top result always scores the same ~0.076 whether the
    #: match is perfect or nonsense, and thresholding on it refused nothing at all.
    top_similarity: float

    used_disease_filter: bool
    used_topic_filter: bool
    fell_back: bool
    query: str
    rewritten_query: str | None = None

    #: Best cross-encoder score, when reranking ran. Preferred over cosine because it
    #: judges whether the passage answers the question, not whether it shares a topic.
    top_rerank_score: float | None = None

    @property
    def is_empty(self) -> bool:
        return not self.passages

    @property
    def best_score(self) -> float:
        return self.passages[0].score if self.passages else 0.0

    @property
    def is_weak(self) -> bool:
        """Whether the best match is too poor to answer from.

        Generation must refuse here rather than paraphrase an irrelevant passage.
        """
        if self.is_empty:
            return True
        if self.top_rerank_score is not None:
            return self.top_rerank_score < MIN_RERANK_SCORE
        return self.top_similarity < MIN_RELEVANCE


def _build_filter(disease: str | None, topic: str | None, language: str | None) -> Any:
    from qdrant_client import models

    conditions = []
    if disease:
        # `general` chunks stay eligible alongside disease-specific ones: cross-cutting
        # guidance on sanitation or tool sterilisation is filed general but answers a
        # panama question perfectly well.
        conditions.append(
            models.FieldCondition(key="disease", match=models.MatchAny(any=[disease, "general"]))
        )
    if topic:
        conditions.append(models.FieldCondition(key="topic", match=models.MatchValue(value=topic)))
    if language:
        conditions.append(
            models.FieldCondition(key="language", match=models.MatchValue(value=language))
        )

    return models.Filter(must=conditions) if conditions else None


def _search(
    embedder: Embedder,
    query: str,
    *,
    collection: str,
    query_filter: Any,
    limit: int,
) -> tuple[list[Any], list[Any]]:
    """Run dense and sparse searches, returning both rankings."""
    from qdrant_client import models

    client = _client()
    embedded = embedder.encode_query(query)

    dense_hits = client.query_points(
        collection_name=collection,
        query=embedded.dense[0].tolist(),
        using="dense",
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    ).points

    sparse_hits: list[Any] = []
    if embedder.produces_sparse and embedded.sparse:
        weights = embedded.sparse[0]
        if weights:
            sparse_hits = client.query_points(
                collection_name=collection,
                query=models.SparseVector(
                    indices=list(weights.keys()), values=list(weights.values())
                ),
                using="sparse",
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            ).points

    return dense_hits, sparse_hits


def reciprocal_rank_fusion(rankings: list[list[Any]], k: int = RRF_K) -> list[tuple[Any, float]]:
    """Merge rankings by rank rather than by score.

    Dense cosine similarity and sparse lexical scores are on different scales and are not
    comparable; normalising them is guesswork. RRF sidesteps that by using position only.
    """
    scores: dict[str, float] = {}
    points: dict[str, Any] = {}

    for ranking in rankings:
        for position, point in enumerate(ranking):
            key = str(point.id)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + position + 1)
            points[key] = point

    ordered = sorted(scores.items(), key=lambda pair: -pair[1])
    return [(points[key], score) for key, score in ordered]


#: Cross-encoder for reranking. A small English model, not the 2.2 GB multilingual one:
#: queries are translated to English before retrieval, so multilingual capacity here would
#: cost 25x the download for capability nothing uses.
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker: Any = None


def _load_reranker() -> Any:
    """Load the cross-encoder once, or return None if it is unavailable."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(RERANKER_MODEL)
        except Exception:
            _reranker = False  # sentinel: tried and failed, do not retry per query
    return _reranker or None


def _rerank(query: str, candidates: list[tuple[Any, float]], top_k: int) -> list[tuple[Any, float]]:
    """Cross-encoder reranking, with a graceful fallback to the fused order.

    A cross-encoder reads the query and passage *together*, so it judges whether a passage
    actually answers the question rather than whether it is merely on the same topic. That
    distinction is what separates "how do I treat sigatoka" from "what does sigatoka cost" --
    dense similarity sees both as banana text.

    Degrades to the fused ranking rather than failing: an imperfect order still beats no
    answer.
    """
    if not candidates:
        return []

    model = _load_reranker()
    if model is None:
        return candidates[:top_k]

    try:
        pairs = [[query, point.payload.get("text", "")] for point, _ in candidates]
        raw = model.predict(pairs)
        scores = [float(s) for s in raw]
    except Exception:
        return candidates[:top_k]

    reranked = sorted(zip(candidates, scores, strict=True), key=lambda item: -item[1])
    return [(point, score) for (point, _), score in reranked][:top_k]


def _apply_preferences(
    results: list[tuple[Any, float]], prefer_region: str | None
) -> list[tuple[Any, float]]:
    """Nudge scores toward more authoritative and more locally applicable sources."""
    adjusted = []
    for point, score in results:
        payload = point.payload or {}
        bonus = _AUTHORITY_BONUS.get(str(payload.get("authority", "")), 0.0)
        if prefer_region and str(payload.get("region", "")) == prefer_region:
            bonus += 0.05
        adjusted.append((point, score + bonus))

    return sorted(adjusted, key=lambda pair: -pair[1])


def _to_retrieved(point: Any, score: float) -> Retrieved:
    payload = point.payload or {}
    return Retrieved(
        chunk_id=str(payload.get("chunk_id", point.id)),
        text=str(payload.get("text", "")),
        context_prefix=str(payload.get("context_prefix", "")),
        score=float(score),
        source=str(payload.get("source", "")),
        title=str(payload.get("title", "")),
        url=str(payload.get("url", "")),
        disease=str(payload.get("disease", "")),
        topic=str(payload.get("topic", "")),
        region=str(payload.get("region", "")),
        authority=str(payload.get("authority", "")),
        heading_path=list(payload.get("heading_path", [])),
    )


def retrieve(
    query: str,
    *,
    disease: str | None = None,
    topic: str | None = None,
    embedder: Embedder | None = None,
    collection: str = COLLECTION_NAME,
    top_k: int = 5,
    candidates: int = 20,
    prefer_region: str | None = "pakistan",
    rerank: bool = True,
    translate: bool = True,
) -> RetrievalResult:
    """Retrieve passages for a question, optionally scoped to a disease.

    ``disease`` normally comes from the CNN. ``prefer_region`` defaults to Pakistan so local
    guidance wins ties — currently a no-op, since no Pakistani source is in the corpus yet,
    but it is the hook that makes adding one immediately effective.
    """
    active = embedder or Embedder()

    # The corpus and the embedder are both English-only, so an Urdu question is translated
    # before anything is searched. Both forms are kept on the result: when an answer is
    # wrong, the first question to ask is whether the translation was.
    from banana_lifeline.rag.translate import translate_query

    translation = translate_query(query, enabled=translate)
    search_text = translation.translated

    attempts: list[tuple[str | None, str | None]] = [(disease, topic)]
    if topic:
        attempts.append((disease, None))  # topic too narrow
    if disease:
        attempts.append((None, None))  # disease filter too narrow

    fell_back = False
    for index, (try_disease, try_topic) in enumerate(attempts):
        query_filter = _build_filter(try_disease, try_topic, language=None)
        dense_hits, sparse_hits = _search(
            active, search_text, collection=collection, query_filter=query_filter, limit=candidates
        )

        top_similarity = max((h.score for h in dense_hits), default=0.0)
        rankings = [r for r in (dense_hits, sparse_hits) if r]
        if not rankings:
            fell_back = True
            continue

        fused = reciprocal_rank_fusion(rankings)
        ranked = _rerank(search_text, fused, candidates) if rerank else fused[:candidates]
        ranked = _apply_preferences(ranked, prefer_region)[:top_k]

        if ranked:
            return RetrievalResult(
                passages=[_to_retrieved(point, score) for point, score in ranked],
                top_similarity=float(top_similarity),
                top_rerank_score=(float(ranked[0][1]) if rerank and ranked else None),
                used_disease_filter=try_disease is not None,
                used_topic_filter=try_topic is not None,
                fell_back=index > 0 or fell_back,
                query=query,
                rewritten_query=search_text if translation.was_translated else None,
            )
        fell_back = True

    return RetrievalResult(
        passages=[],
        top_similarity=0.0,
        used_disease_filter=False,
        used_topic_filter=False,
        fell_back=True,
        query=query,
    )
