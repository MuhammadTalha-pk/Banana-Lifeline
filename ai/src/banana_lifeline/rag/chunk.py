"""Split parsed documents into retrievable chunks.

Splitting happens on **headings first, size second**. These are structured technical
documents; a fixed-width split would cut "Chemical control" in half and leave the dosage
stranded in a chunk that no longer mentions the disease.

Each chunk is prefixed with a short context line naming its document and section. That
matters more than it sounds: retrieved in isolation, a paragraph reading *"Apply the second
treatment 14 days later"* is unusable — the reader cannot tell which disease, which product,
or which second treatment. The prefix restores what the surrounding page made obvious.

The prefix is deterministic (document title plus heading path) rather than LLM-generated.
It costs nothing, cannot hallucinate, and captures most of the benefit; an optional model
pass can refine it later without changing this contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from banana_lifeline.config import Paths

#: Target chunk size in tokens. Roughly four characters per token for English prose.
TARGET_TOKENS = 500
OVERLAP_TOKENS = 80
MIN_CHUNK_TOKENS = 40
CHARS_PER_TOKEN = 4

_HEADING = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(slots=True)
class Chunk:
    """One retrievable passage, carrying everything needed to cite and filter it."""

    chunk_id: str
    text: str
    context_prefix: str

    # provenance / the metadata schema
    slug: str
    source: str
    title: str
    url: str
    authority: str
    region: str
    document_type: str
    language: str
    year: int | None
    licence: str

    # assigned later by classify.py
    disease: str = "general"
    topic: str = "general"

    heading_path: list[str] = field(default_factory=list)
    n_tokens: int = 0
    document_position: float = 0.0

    @property
    def embedding_text(self) -> str:
        """What actually gets embedded: the context line followed by the passage."""
        return f"{self.context_prefix}\n\n{self.text}"

    def citation(self) -> str:
        section = " > ".join(self.heading_path) if self.heading_path else ""
        return f"{self.source} — {self.title}" + (f" ({section})" if section else "")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_sections(text: str) -> list[tuple[list[str], str]]:
    """Split on ``## `` markers, tracking the heading hierarchy.

    Returns ``(heading_path, body)`` pairs. Text before the first heading is kept under an
    empty path rather than discarded -- it is usually the document's opening summary, which
    is often the single most useful passage in the file.
    """
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [([], text.strip())]

    sections: list[tuple[list[str], str]] = []

    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(([], preamble))

    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append(([heading], body))

    return sections


def _split_long_body(body: str, target: int, overlap: int) -> list[str]:
    """Split an oversized section on sentence boundaries, with overlap.

    Overlap exists so a fact spanning a boundary survives in at least one chunk intact.
    """
    if estimate_tokens(body) <= target:
        return [body]

    sentences = _SENTENCE_END.split(body)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)

        if current_tokens + sentence_tokens > target and current:
            chunks.append(" ".join(current).strip())

            # Carry the tail of this chunk into the next one.
            carried: list[str] = []
            carried_tokens = 0
            for previous in reversed(current):
                previous_tokens = estimate_tokens(previous)
                if carried_tokens + previous_tokens > overlap:
                    break
                carried.insert(0, previous)
                carried_tokens += previous_tokens

            current = carried
            current_tokens = carried_tokens

        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        chunks.append(" ".join(current).strip())

    return [c for c in chunks if c]


def build_context_prefix(title: str, source: str, heading_path: list[str]) -> str:
    """The situating line prepended before embedding."""
    location = " > ".join(heading_path) if heading_path else "introduction"
    return f'From {source}\'s "{title}", section: {location}.'


def chunk_document(
    text: str,
    meta: dict[str, Any],
    *,
    filename: str,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Turn one parsed document into chunks."""
    slug = str(meta.get("slug", "unknown"))
    title = str(meta.get("title", slug))
    source = str(meta.get("source", "unknown"))

    sections = _split_sections(text)
    chunks: list[Chunk] = []
    stem = Path(filename).stem

    # A multi-file source shares one registry title across every file, so the *chapter* it
    # came from is otherwise lost. Hawaii's guidebook is 14 chapters under one title; without
    # this, chunks from "Fusarium Wilt or Panama Disease" carry no hint of their subject and
    # classify as `general`. The document's own first heading is the missing signal.
    document_title = sections[0][0][0] if sections and sections[0][0] else ""
    if not document_title:
        for path, _body in sections:
            if path:
                document_title = path[0]
                break

    for section_index, (heading_path, body) in enumerate(sections):
        # Root every chunk at the document's own title so its subject travels with it.
        full_path = heading_path
        if document_title and document_title not in heading_path:
            full_path = [document_title, *heading_path]

        for part_index, part in enumerate(_split_long_body(body, target_tokens, overlap_tokens)):
            if estimate_tokens(part) < MIN_CHUNK_TOKENS:
                continue  # fragments this small are headings or stray captions

            chunks.append(
                Chunk(
                    chunk_id=f"{slug}__{stem}__{section_index:03d}_{part_index:02d}",
                    text=part,
                    context_prefix=build_context_prefix(title, source, full_path),
                    slug=slug,
                    source=source,
                    title=title,
                    url=str(meta.get("url", "")),
                    authority=str(meta.get("authority", "")),
                    region=str(meta.get("region", "")),
                    document_type=str(meta.get("document_type", "")),
                    language=str(meta.get("language", "en")),
                    year=meta.get("year"),
                    licence=str(meta.get("licence", "")),
                    heading_path=full_path,
                    n_tokens=estimate_tokens(part),
                )
            )

    # Relative position, so retrieval can prefer early passages when scores tie -- overviews
    # tend to answer a farmer's question better than an appendix does.
    total = max(len(chunks), 1)
    for position, chunk in enumerate(chunks):
        chunk.document_position = position / total

    return chunks


def chunk_corpus(paths: Paths, **kwargs: Any) -> list[Chunk]:
    """Chunk every parsed document, re-attaching its provenance."""
    text_dir = paths.corpus / "text"
    manifest_path = text_dir / "_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No parsed corpus at {text_dir}. Run `banana rag parse` first.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_root = paths.corpus / "raw"

    provenance: dict[str, dict[str, Any]] = {}
    for provenance_path in raw_root.glob("*/_provenance.json"):
        meta = json.loads(provenance_path.read_text(encoding="utf-8"))
        provenance[str(meta["slug"])] = meta

    chunks: list[Chunk] = []
    for entry in manifest:
        if not entry.get("usable") or not entry.get("text_file"):
            continue
        text = (text_dir / entry["text_file"]).read_text(encoding="utf-8")
        meta = provenance.get(entry["slug"], {"slug": entry["slug"]})
        chunks.extend(chunk_document(text, meta, filename=entry["filename"], **kwargs))

    return chunks


def write_chunks(chunks: list[Chunk], paths: Paths) -> Path:
    """Write chunks as JSONL, one object per line."""
    paths.corpus.mkdir(parents=True, exist_ok=True)
    destination = paths.corpus / "chunks.jsonl"

    with destination.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    return destination


def read_chunks(paths: Paths) -> list[Chunk]:
    source = paths.corpus / "chunks.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"No chunks at {source}. Run `banana rag chunk` first.")

    with source.open("r", encoding="utf-8") as handle:
        return [Chunk(**json.loads(line)) for line in handle if line.strip()]
