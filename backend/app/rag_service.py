from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader
from qdrant_client import QdrantClient, models

from .schemas import SourceRef
from .settings import get_settings


class RagNotReady(RuntimeError):
    pass


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    source: SourceRef


@lru_cache(maxsize=1)
def _embedder():
    try:
        from FlagEmbedding import BGEM3FlagModel
    except Exception as exc:
        raise RagNotReady('FlagEmbedding is not installed.') from exc

    settings = get_settings()
    return BGEM3FlagModel(settings.embedding_model, use_fp16=False)


@lru_cache(maxsize=1)
def _qdrant() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_url:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    settings.qdrant_local_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.qdrant_local_path))


def _embed(texts: list[str]) -> list[list[float]]:
    output = _embedder().encode(
        texts,
        batch_size=min(8, max(1, len(texts))),
        max_length=8192,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return output['dense_vecs'].tolist()


def _chunks(text: str, *, size: int = 1800, overlap: int = 220) -> Iterable[str]:
    cleaned = ' '.join(text.replace('\x00', ' ').split())
    if not cleaned:
        return
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        chunk = cleaned[start:end].strip()
        if chunk:
            yield chunk
        if end == len(cleaned):
            break
        start = max(start + 1, end - overlap)


def _iter_documents(root: Path):
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == '.pdf':
            reader = PdfReader(str(path))
            for page_index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ''
                for chunk_index, chunk in enumerate(_chunks(text)):
                    yield {
                        'text': chunk,
                        'title': path.stem,
                        'source': str(path.name),
                        'page': page_index,
                        'chunk_index': chunk_index,
                    }
        elif suffix in {'.txt', '.md'}:
            text = path.read_text(encoding='utf-8', errors='ignore')
            for chunk_index, chunk in enumerate(_chunks(text)):
                yield {
                    'text': chunk,
                    'title': path.stem,
                    'source': str(path.name),
                    'page': None,
                    'chunk_index': chunk_index,
                }


def index_knowledge(*, recreate: bool = False) -> int:
    settings = get_settings()
    root = settings.knowledge_dir.resolve()
    if not root.is_dir():
        raise RagNotReady(f'Knowledge directory does not exist: {root}')

    docs = list(_iter_documents(root))
    if not docs:
        raise RagNotReady('No PDF/MD/TXT knowledge documents were found.')

    client = _qdrant()
    name = settings.qdrant_collection

    sample_vector = _embed([docs[0]['text']])[0]
    vector_size = len(sample_vector)

    if recreate and client.collection_exists(name):
        client.delete_collection(name)

    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    batch_size = 24
    total = 0
    for start in range(0, len(docs), batch_size):
        batch = docs[start : start + batch_size]
        vectors = _embed([item['text'] for item in batch])
        points = []
        for item, vector in zip(batch, vectors, strict=True):
            key = (
                f"{item['source']}|{item['page']}|{item['chunk_index']}|"
                f"{hashlib.sha256(item['text'].encode('utf-8')).hexdigest()}"
            )
            point_id = str(uuid.UUID(hashlib.md5(key.encode('utf-8')).hexdigest()))
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=item,
                )
            )
        client.upsert(collection_name=name, points=points, wait=True)
        total += len(points)
    return total


def is_rag_ready() -> bool:
    settings = get_settings()
    try:
        return _qdrant().collection_exists(settings.qdrant_collection)
    except Exception:
        return False


def retrieve(question: str, *, limit: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    client = _qdrant()
    if not client.collection_exists(settings.qdrant_collection):
        raise RagNotReady(
            'RAG index is not built. Run `python -m app.index_knowledge` first.'
        )

    vector = _embed([question])[0]
    result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        with_payload=True,
        limit=limit or settings.rag_top_k,
    ).points

    chunks: list[RetrievedChunk] = []
    for point in result:
        payload = point.payload or {}
        text = str(payload.get('text') or '').strip()
        if not text:
            continue
        chunks.append(
            RetrievedChunk(
                text=text,
                source=SourceRef(
                    title=str(payload.get('title') or payload.get('source') or 'Knowledge source'),
                    source=str(payload.get('source') or ''),
                    page=int(payload['page']) if payload.get('page') is not None else None,
                    score=float(point.score) if point.score is not None else None,
                ),
            )
        )
    return chunks
