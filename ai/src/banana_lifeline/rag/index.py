"""Qdrant collection management.

One collection with two named vectors — ``dense`` for meaning, ``sparse`` for exact terms —
so hybrid search needs no second system to keep in sync.

Payload indexes on ``disease``, ``topic``, and ``region`` exist because those are the fields
retrieval filters on before it searches. Without them Qdrant filters by scanning, which is
fine at 400 chunks and not fine later; declaring them now costs nothing and avoids a silent
performance cliff.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from banana_lifeline.rag.embed import Embedder

if TYPE_CHECKING:
    from banana_lifeline.rag.chunk import Chunk

COLLECTION_NAME = "banana_knowledge"

#: Fields retrieval filters on. Indexed so filtering stays cheap as the corpus grows.
INDEXED_PAYLOAD_FIELDS = ("disease", "topic", "region", "authority", "slug", "language")


@dataclass(slots=True)
class IndexStats:
    collection: str
    n_points: int
    dense_dim: int
    has_sparse: bool
    model: str


@lru_cache(maxsize=4)
def _client(url: str | None = None, api_key: str | None = None) -> Any:
    """The Qdrant client for this process, connection and all.

    Cached because the collection is on a cloud cluster: an uncached client meant a fresh
    TLS handshake per call, and ``_search`` builds two calls per question. That was ~5s of a
    ~9s query spent re-establishing a connection that was already available.
    """
    from qdrant_client import QdrantClient

    from banana_lifeline.secrets import load_credentials

    credentials = load_credentials()
    resolved_url = url or credentials.qdrant_url
    if not resolved_url:
        raise RuntimeError(
            "No Qdrant URL configured. Add QDRANT_URL to ai/.env — an API key alone cannot connect."
        )
    return QdrantClient(url=resolved_url, api_key=api_key or credentials.qdrant_api_key, timeout=60)


def _point_id(chunk_id: str) -> str:
    """Deterministic UUID from a chunk id.

    Qdrant requires UUID or integer ids, but re-indexing must overwrite rather than
    duplicate — so the id is derived from the chunk id instead of generated randomly.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def create_collection(
    embedder: Embedder,
    *,
    collection: str = COLLECTION_NAME,
    recreate: bool = False,
) -> None:
    """Create the collection with named dense and sparse vectors."""
    from qdrant_client import models

    client = _client()
    exists = client.collection_exists(collection)

    if exists and not recreate:
        return
    if exists:
        client.delete_collection(collection)

    client.create_collection(
        collection_name=collection,
        vectors_config={
            "dense": models.VectorParams(size=embedder.dimension, distance=models.Distance.COSINE)
        },
        sparse_vectors_config=(
            {"sparse": models.SparseVectorParams()} if embedder.produces_sparse else {}
        ),
    )

    for field in INDEXED_PAYLOAD_FIELDS:
        client.create_payload_index(
            collection_name=collection,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def index_chunks(
    chunks: list[Chunk],
    embedder: Embedder,
    *,
    collection: str = COLLECTION_NAME,
    batch_size: int = 16,
    recreate: bool = True,
    progress: Any = None,
) -> IndexStats:
    """Embed and upload every chunk."""
    from qdrant_client import models

    create_collection(embedder, collection=collection, recreate=recreate)
    client = _client()

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embedded = embedder.encode([c.embedding_text for c in batch])

        points = []
        for offset, chunk in enumerate(batch):
            vector: dict[str, Any] = {"dense": embedded.dense[offset].tolist()}
            if embedded.sparse is not None:
                weights = embedded.sparse[offset]
                if weights:
                    vector["sparse"] = models.SparseVector(
                        indices=list(weights.keys()), values=list(weights.values())
                    )

            points.append(
                models.PointStruct(
                    id=_point_id(chunk.chunk_id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "context_prefix": chunk.context_prefix,
                        # the metadata schema, verbatim
                        "source": chunk.source,
                        "disease": chunk.disease,
                        "topic": chunk.topic,
                        "region": chunk.region,
                        "authority": chunk.authority,
                        "document_type": chunk.document_type,
                        "language": chunk.language,
                        "year": chunk.year,
                        # citation support
                        "slug": chunk.slug,
                        "title": chunk.title,
                        "url": chunk.url,
                        "licence": chunk.licence,
                        "heading_path": chunk.heading_path,
                        "document_position": chunk.document_position,
                    },
                )
            )

        client.upsert(collection_name=collection, points=points, wait=True)
        if progress is not None:
            progress(min(start + batch_size, len(chunks)), len(chunks))

    info = client.get_collection(collection)
    return IndexStats(
        collection=collection,
        n_points=int(info.points_count or 0),
        dense_dim=embedder.dimension,
        has_sparse=embedder.produces_sparse,
        model=embedder.model_name,
    )


def collection_stats(collection: str = COLLECTION_NAME) -> dict[str, Any]:
    client = _client()
    if not client.collection_exists(collection):
        return {"exists": False}

    info = client.get_collection(collection)
    return {
        "exists": True,
        "points": int(info.points_count or 0),
        "status": str(info.status),
    }
