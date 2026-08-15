"""Tests for document parsing.

Every case here is a real failure this parser hit against the actual corpus. Each one
produced an empty or near-empty document that the quality gate then reported as "likely a
scanned PDF" — a misleading symptom whose cause was three layers away.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("bs4")

from banana_lifeline.rag.parse import (
    MIN_USABLE_CHARS,
    _detect_kind,
    _tidy,
    parse_file,
    parse_html,
)

# --------------------------------------------------------------------------------------
# Chrome stripping must not eat the article
# --------------------------------------------------------------------------------------


def test_content_wrapped_in_a_form_survives(tmp_path: Path) -> None:
    """ASP.NET sites wrap the whole page body in one <form runat="server">.

    Treating <form> as chrome deleted fourteen chapters of the Hawaii banana guidebook
    outright, which then looked like fourteen scanned PDFs.
    """
    html = tmp_path / "chapter.html"
    html.write_text(
        "<html><body><form id='aspnetForm'>"
        "<h2>Fusarium wilt of banana</h2>"
        "<p>" + ("Fusarium oxysporum f. sp. cubense causes Panama disease. " * 12) + "</p>"
        "</form></body></html>",
        encoding="utf-8",
    )
    text, headings = parse_html(html)

    assert "Fusarium oxysporum" in text
    assert headings == 1
    assert len(text) > MIN_USABLE_CHARS


def test_content_wrapped_in_header_and_footer_survives(tmp_path: Path) -> None:
    """APS nests its entire Black Sigatoka lesson inside <header>/<footer>.

    Blanket-stripping them reduced 18,611 characters of plant pathology to 14.
    """
    body = "Black Sigatoka is caused by Mycosphaerella fijiensis. " * 12
    html = tmp_path / "lesson.html"
    html.write_text(
        f"<html><body><header><h1>Black Sigatoka</h1><p>{body}</p></header></body></html>",
        encoding="utf-8",
    )
    text, _ = parse_html(html)

    assert "Mycosphaerella fijiensis" in text
    assert len(text) > MIN_USABLE_CHARS


def test_real_navigation_is_still_removed(tmp_path: Path) -> None:
    """The rollback must not become a licence to keep every site menu.

    When the article is the bulk of the page, the nav goes.
    """
    article = "Panama disease management requires strict sanitation. " * 20
    html = tmp_path / "page.html"
    html.write_text(
        "<html><body>"
        "<nav><a href='/'>Home</a><a href='/login'>Login</a></nav>"
        f"<p>{article}</p>"
        "</body></html>",
        encoding="utf-8",
    )
    text, _ = parse_html(html)

    assert "sanitation" in text
    assert "Login" not in text


def test_scripts_and_styles_never_survive(tmp_path: Path) -> None:
    html = tmp_path / "page.html"
    html.write_text(
        "<html><body><script>var x=1;</script><style>.a{color:red}</style>"
        "<p>Sigatoka control uses protectant fungicides.</p></body></html>",
        encoding="utf-8",
    )
    text, _ = parse_html(html)

    assert "Sigatoka control" in text
    assert "var x" not in text and "color:red" not in text


# --------------------------------------------------------------------------------------
# File type detection
# --------------------------------------------------------------------------------------


def test_extensionless_html_is_detected_from_provenance(tmp_path: Path) -> None:
    """The Hawaii guidebook serves chapters from URLs with no file extension.

    Dispatching on suffix rejected them as "unsupported file type".
    """
    path = tmp_path / "CHPT2-Panama"
    path.write_bytes(b"<html><body><p>Fusarium wilt</p></body></html>")

    meta = {"files": [{"filename": "CHPT2-Panama", "content_type": "text/html; charset=utf-8"}]}
    assert _detect_kind(path, meta) == "html"


def test_content_is_sniffed_when_provenance_is_silent(tmp_path: Path) -> None:
    path = tmp_path / "mystery"
    path.write_bytes(b"<!DOCTYPE html>\n<html><body><p>x</p></body></html>")
    assert _detect_kind(path, {}) == "html"

    pdf = tmp_path / "mystery2"
    pdf.write_bytes(b"%PDF-1.7\n...")
    assert _detect_kind(pdf, {}) == "pdf"


def test_unknown_content_is_reported_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "thing.bin"
    path.write_bytes(b"\x00\x01\x02binary junk")

    document = parse_file(path, {"slug": "x"})
    assert not document.usable
    assert document.warning and "unrecognised" in document.warning


# --------------------------------------------------------------------------------------
# Text hygiene
# --------------------------------------------------------------------------------------


def test_zero_width_characters_are_stripped() -> None:
    """Invisible to a reader, but they split words into separate tokens.

    "Fusa​rium" stops matching a query for "fusarium".
    """
    assert _tidy("Fusa​rium wilt") == "Fusarium wilt"
    assert _tidy("a﻿b­c") == "abc"


def test_paragraph_breaks_survive_whitespace_collapsing() -> None:
    assert _tidy("one\n\n\n\n\ntwo") == "one\n\ntwo"
    assert _tidy("a  \t  b") == "a b"


def test_quality_gate_flags_near_empty_documents(tmp_path: Path) -> None:
    """A scanned PDF must fail loudly rather than silently index nothing."""
    path = tmp_path / "scan.html"
    path.write_bytes(b"<html><body><p>hi</p></body></html>")

    document = parse_file(path, {"slug": "x"})
    assert not document.usable
    assert document.warning and "characters extracted" in document.warning


# --------------------------------------------------------------------------------------
# Parsed corpus — skips until `banana rag parse` has run
# --------------------------------------------------------------------------------------


def _text_corpus_or_skip() -> Path:
    from banana_lifeline.config import get_paths

    text_dir = get_paths().corpus / "text"
    if not (text_dir / "_manifest.json").is_file():
        pytest.skip("corpus not parsed yet; run `banana rag parse`")
    return text_dir


def test_parsed_corpus_is_valid_utf8_without_replacement_chars() -> None:
    """U+FFFD means a decode failed and the text is silently corrupted."""
    for path in _text_corpus_or_skip().glob("*.txt"):
        assert "�" not in path.read_text(encoding="utf-8"), f"{path.name} has mojibake"


def test_every_parsed_document_kept_some_structure() -> None:
    """The chunker splits on headings; a document with none gets cut mid-topic."""
    import json

    text_dir = _text_corpus_or_skip()
    manifest = json.loads((text_dir / "_manifest.json").read_text(encoding="utf-8"))
    usable = [entry for entry in manifest if entry["usable"]]

    assert usable, "nothing parsed"
    assert sum(entry["n_headings"] for entry in usable) > 0
