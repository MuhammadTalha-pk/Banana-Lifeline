"""Parse fetched documents into structured text.

Output is plain text with headings preserved as explicit ``## `` markers, because the
chunker splits on structure rather than on character count. Losing headings here would
force the chunker to cut mid-topic later.

Two failure modes are treated as errors rather than absorbed silently:

* **A scanned PDF** extracts almost no text. Indexing it would add an empty document that
  quietly contributes nothing to every future answer.
* **A page that is mostly navigation** yields boilerplate. If a retrieval hit turns out to
  be a site menu, the answer built on it is worthless.

Both are caught by a quality gate that reports, rather than by a filter that hides.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from banana_lifeline.config import Paths

# Below this, a "document" is almost certainly a scan, an error page, or navigation chrome.
MIN_USABLE_CHARS = 400

# Sections whose content is never agronomy. Matched against heading text.
_BOILERPLATE_HEADINGS = re.compile(
    r"^\s*(navigation|menu|search|login|sign in|cookie|privacy|terms|copyright|"
    r"related links|share this|follow us|contact us|site map|breadcrumb)\s*$",
    re.IGNORECASE,
)

_WHITESPACE = re.compile(r"[ \t\xa0]+")
_BLANK_RUNS = re.compile(r"\n{3,}")

# Zero-width and directional marks. Invisible to a reader but not to a tokeniser: they split
# words into separate tokens, so "Fusarium" with one embedded becomes two meaningless pieces
# and stops matching the query "fusarium".
# RUF001 is suppressed on each line below on purpose: these ARE the ambiguous
# characters, and the pattern exists precisely to strip them. Escape sequences would
# read better, but `ruff format` rewrites them back into literals.
_INVISIBLE = re.compile(
    "[​-‏"
    "  "  # noqa: RUF001 - line and paragraph separators
    "﻿­]"
)


@dataclass(slots=True)
class ParsedDocument:
    """One source document reduced to structured text."""

    slug: str
    filename: str
    text: str
    n_chars: int
    n_headings: int
    source_meta: dict[str, Any] = field(default_factory=dict)
    warning: str | None = None

    @property
    def usable(self) -> bool:
        return self.n_chars >= MIN_USABLE_CHARS and self.warning is None


def _tidy(text: str) -> str:
    """Collapse whitespace without destroying paragraph boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INVISIBLE.sub("", text)
    text = _WHITESPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_RUNS.sub("\n\n", text).strip()


def parse_pdf(path: Path) -> tuple[str, int]:
    """Extract text from a PDF, inferring headings from short standalone lines.

    PDFs carry no heading markup, so structure has to be inferred. A line that is short,
    title-cased or numbered, and sits alone is almost always a heading in a technical
    manual — good enough to give the chunker something real to split on.
    """
    from pypdf import PdfReader

    reader = PdfReader(path)
    parts: list[str] = []
    headings = 0

    for page in reader.pages:
        raw = page.extract_text() or ""
        for line in _tidy(raw).split("\n"):
            stripped = line.strip()
            if not stripped:
                parts.append("")
                continue

            looks_like_heading = (
                len(stripped) < 80
                and not stripped.endswith((".", ",", ";", ":"))
                and (
                    re.match(r"^\d+(\.\d+)*\.?\s+\S", stripped)  # "4.2 Soil management"
                    or (stripped.istitle() and len(stripped.split()) <= 8)
                    or (stripped.isupper() and 3 < len(stripped) < 60)
                )
            )
            if looks_like_heading and not _BOILERPLATE_HEADINGS.match(stripped):
                parts.append(f"\n## {stripped}\n")
                headings += 1
            else:
                parts.append(stripped)

    return _tidy("\n".join(parts)), headings


#: Never carries readable content, whatever the site does.
_ALWAYS_STRIP = ("script", "style", "noscript", "iframe")

#: Usually chrome, but some sites wrap their whole article inside one of these. Stripped
#: only when doing so leaves the bulk of the text behind.
#:
#: ``form`` is here, not above, because ASP.NET WebForms sites (the Hawaii CTAHR CMS among
#: them) wrap the entire page body in a single ``<form runat="server">``. Treating that as
#: chrome deleted fourteen chapters of banana pathology outright.
_MAYBE_STRIP = ("nav", "header", "footer", "form", "aside")

#: A trim is kept only if this much of the original text survives it.
_MIN_SURVIVING_FRACTION = 0.5


def _extract_body(raw: bytes) -> Any:
    """Return a soup body with chrome removed, without deleting the article itself.

    Blanket-stripping structural tags is the obvious approach and it is wrong on real sites.
    APS nests its whole Black Sigatoka lesson inside ``<header>``/``<footer>``; Hawaii wraps
    every chapter in a ``<form>``. Both produced near-empty documents that then looked like
    scanned PDFs to the quality gate.

    So each removal is attempted and rolled back if it took most of the page with it.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(list(_ALWAYS_STRIP)):
        tag.decompose()

    body = soup.body or soup
    baseline = len(body.get_text(strip=True))
    if baseline == 0:
        return body

    # Strip one tag type at a time so a single greedy container cannot veto the rest.
    for tag_name in _MAYBE_STRIP:
        trial = BeautifulSoup(str(body), "html.parser")
        for tag in trial(tag_name):
            tag.decompose()

        if len(trial.get_text(strip=True)) >= baseline * _MIN_SURVIVING_FRACTION:
            body = trial

    return body


def parse_html(path: Path) -> tuple[str, int]:
    """Extract readable text from an HTML page, dropping navigation and scripts."""
    body = _extract_body(path.read_bytes())

    parts: list[str] = []
    headings = 0

    for element in body.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "pre"]):
        text = _tidy(element.get_text(" ", strip=True))
        if not text:
            continue

        if element.name in {"h1", "h2", "h3", "h4"}:
            if _BOILERPLATE_HEADINGS.match(text):
                continue
            parts.append(f"\n## {text}\n")
            headings += 1
        elif element.name == "li":
            parts.append(f"- {text}")
        else:
            parts.append(text)

    if not parts:  # some pages use bare divs; fall back to the whole body
        parts = [_tidy(body.get_text("\n", strip=True))]

    return _tidy("\n".join(parts)), headings


def _detect_kind(path: Path, source_meta: dict[str, Any]) -> str:
    """Decide how to parse a file: ``"pdf"``, ``"html"``, or ``"unknown"``.

    Filename extension is the least reliable signal and cannot be the primary one. The
    Hawaii guidebook serves its chapters from extensionless URLs (``/Guidebook/CHPT2-Panama``),
    so suffix-based dispatch rejected fourteen on-topic chapters as "unsupported file type".
    Content type from provenance is authoritative; sniffing the bytes is the backstop.
    """
    for entry in source_meta.get("files", []):
        if entry.get("filename") == path.name:
            content_type = str(entry.get("content_type", "")).lower()
            if "pdf" in content_type:
                return "pdf"
            if "html" in content_type or "xml" in content_type:
                return "html"
            break

    head = path.read_bytes()[:1024].lstrip().lower()
    if head.startswith(b"%pdf"):
        return "pdf"
    if b"<html" in head or b"<!doctype html" in head:
        return "html"

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".htm", ".html"}:
        return "html"
    return "unknown"


def parse_file(path: Path, source_meta: dict[str, Any]) -> ParsedDocument:
    """Parse one file, flagging anything that came out suspiciously thin."""
    slug = source_meta.get("slug", path.parent.name)

    try:
        kind = _detect_kind(path, source_meta)
        if kind == "pdf":
            text, headings = parse_pdf(path)
        elif kind == "html":
            text, headings = parse_html(path)
        else:
            return ParsedDocument(
                slug=slug,
                filename=path.name,
                text="",
                n_chars=0,
                n_headings=0,
                source_meta=source_meta,
                warning=f"unrecognised content: {path.name}",
            )
    except Exception as exc:
        return ParsedDocument(
            slug=slug,
            filename=path.name,
            text="",
            n_chars=0,
            n_headings=0,
            source_meta=source_meta,
            warning=f"{type(exc).__name__}: {exc}",
        )

    warning = None
    if len(text) < MIN_USABLE_CHARS:
        warning = (
            f"only {len(text)} characters extracted — likely a scanned PDF needing OCR, "
            "an error page, or pure navigation"
        )

    return ParsedDocument(
        slug=slug,
        filename=path.name,
        text=text,
        n_chars=len(text),
        n_headings=headings,
        source_meta=source_meta,
        warning=warning,
    )


def parse_corpus(paths: Paths) -> list[ParsedDocument]:
    """Parse every fetched document, carrying provenance through to the output."""
    raw_root = paths.corpus / "raw"
    if not raw_root.is_dir():
        raise FileNotFoundError(f"No fetched corpus at {raw_root}. Run `banana rag fetch` first.")

    documents: list[ParsedDocument] = []
    for provenance_path in sorted(raw_root.glob("*/_provenance.json")):
        meta = json.loads(provenance_path.read_text(encoding="utf-8"))
        for file_path in sorted(provenance_path.parent.iterdir()):
            if file_path.name == "_provenance.json" or file_path.is_dir():
                continue
            documents.append(parse_file(file_path, meta))

    return documents


def write_text_corpus(documents: list[ParsedDocument], paths: Paths) -> Path:
    """Write parsed text plus a manifest describing what was and was not usable."""
    destination = paths.corpus / "text"
    destination.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for document in documents:
        record: dict[str, Any] = {
            "slug": document.slug,
            "filename": document.filename,
            "n_chars": document.n_chars,
            "n_headings": document.n_headings,
            "usable": document.usable,
            "warning": document.warning,
        }

        if document.usable:
            out_name = f"{document.slug}__{Path(document.filename).stem}.txt"
            (destination / out_name).write_text(document.text, encoding="utf-8")
            record["text_file"] = out_name

        manifest.append(record)

    (destination / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return destination
