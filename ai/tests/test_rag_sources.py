"""Tests for the source registry and the fetcher.

Network access is never required: the link-resolution logic is tested against fixture HTML,
and the corpus-dependent checks skip when nothing has been fetched.
"""

from __future__ import annotations

import pytest

from banana_lifeline.rag.sources import (
    GENERAL,
    PANAMA,
    REGISTRY,
    SIGATOKA,
    Authority,
    FetchMode,
    by_slug,
    coverage_summary,
    for_disease,
)

# --------------------------------------------------------------------------------------
# Registry integrity
# --------------------------------------------------------------------------------------


def test_slugs_are_unique() -> None:
    """Slugs become directory names and citation keys; a collision silently overwrites."""
    slugs = [s.slug for s in REGISTRY]
    assert len(slugs) == len(set(slugs))


def test_every_disease_has_a_source() -> None:
    """A disease the classifier can predict but the corpus cannot explain is a dead end."""
    for disease in (PANAMA, SIGATOKA, GENERAL):
        assert for_disease(disease), f"no source covers {disease}"


def test_disease_vocabulary_matches_the_classifier() -> None:
    """Retrieval filters on the CNN's own label, so the vocabularies must not drift apart."""
    from banana_lifeline.config import CLASS_NAMES

    covered = {d for s in REGISTRY for d in s.diseases}
    for name in CLASS_NAMES:
        if name == "healthy":
            continue  # healthy plants need no disease guidance
        assert name in covered, f"classifier can predict {name} but no source covers it"


def test_sources_are_ordered_by_authority() -> None:
    """FAO must outrank a university summary when the two disagree."""
    ordered = for_disease(PANAMA)
    tiers = [s.authority for s in ordered]
    assert tiers[0] is Authority.INTERNATIONAL
    assert tiers == sorted(tiers, key=lambda t: list(Authority).index(t))


def test_index_and_landing_sources_declare_a_link_pattern() -> None:
    """Without a pattern these modes would either fetch nothing or crawl a whole site."""
    for source in REGISTRY:
        if source.fetch_mode in (FetchMode.INDEX, FetchMode.LANDING):
            assert source.link_pattern, f"{source.slug} needs a link_pattern"


def test_every_source_records_a_licence() -> None:
    """Redistribution terms are recorded per document, not assumed."""
    for source in REGISTRY:
        assert source.licence.strip(), f"{source.slug} has no licence recorded"


def test_by_slug_rejects_unknown() -> None:
    with pytest.raises(KeyError, match="Unknown source slug"):
        by_slug("does_not_exist")


def test_coverage_reports_the_pakistan_gap() -> None:
    """The absent-local-sources problem must stay visible, not get quietly forgotten.

    Pesticide registration is jurisdiction-specific; when this count becomes non-zero the
    generation layer can drop its "verify local registration" caveat.
    """
    summary = coverage_summary()
    assert summary["pakistani_sources"] == 0
    assert "pakistan" not in summary["regions"]


# --------------------------------------------------------------------------------------
# Link resolution
# --------------------------------------------------------------------------------------


def test_anchor_fragments_collapse_to_one_document() -> None:
    """A table of contents links one chapter file once per section.

    Regression test: treating `page.htm#ch4.1` and `page.htm#ch4.2` as distinct URLs made
    the fetcher download FAO's chapter files up to five times each and overwrite them, which
    is both wasteful and impolite to a public server.
    """
    pytest.importorskip("bs4")
    from banana_lifeline.rag.fetch import _resolve_links

    html = b"""
    <html><body>
      <a href="T0308E04.htm#ch4">4</a>
      <a href="T0308E04.htm#ch4.1">4.1</a>
      <a href="T0308E04.htm#ch4.2">4.2</a>
      <a href="T0308E05.htm#ch5">5</a>
    </body></html>
    """
    links = _resolve_links(html, "https://www.fao.org/4/t0308e/", r"t0308e\d+\.htm", limit=40)

    assert len(links) == 2
    assert all("#" not in link for link in links)


def test_link_limit_is_enforced() -> None:
    """A too-loose pattern must not walk an entire site."""
    pytest.importorskip("bs4")
    from banana_lifeline.rag.fetch import _resolve_links

    html = (
        b"<html><body>"
        + b"".join(f'<a href="doc{i}.pdf">{i}</a>'.encode() for i in range(100))
        + b"</body></html>"
    )

    assert len(_resolve_links(html, "https://example.org/", r"\.pdf", limit=5)) == 5


def test_relative_links_become_absolute() -> None:
    pytest.importorskip("bs4")
    from banana_lifeline.rag.fetch import _resolve_links

    html = b'<html><body><a href="/guide/CHPT2-Panama">Panama</a></body></html>'
    links = _resolve_links(html, "https://cms.example.edu/x/y", r"CHPT", limit=10)

    assert links == ["https://cms.example.edu/guide/CHPT2-Panama"]


def test_safe_name_strips_dangerous_characters() -> None:
    from banana_lifeline.rag.fetch import _safe_name

    name = _safe_name("https://x.org/a%20b/../c d?e=1", "fallback.pdf")
    assert "/" not in name and "?" not in name and " " not in name


# --------------------------------------------------------------------------------------
# Fetched corpus — skips until `banana rag fetch` has run
# --------------------------------------------------------------------------------------


def _corpus_or_skip() -> object:
    from banana_lifeline.config import get_paths

    raw = get_paths().corpus / "raw"
    if not raw.is_dir() or not any(raw.glob("*/_provenance.json")):
        pytest.skip("corpus not fetched yet; run `banana rag fetch`")
    return raw


def test_every_fetched_source_has_provenance() -> None:
    """An answer citing a source must be able to name its publisher and retrieval date."""
    import json

    raw = _corpus_or_skip()
    for prov in raw.glob("*/_provenance.json"):  # type: ignore[attr-defined]
        meta = json.loads(prov.read_text(encoding="utf-8"))
        for field in ("slug", "url", "source", "authority", "region", "licence", "fetched_at"):
            assert meta.get(field), f"{prov.parent.name} is missing provenance field {field!r}"
        assert meta["files"], f"{prov.parent.name} recorded no files"


def test_fetched_files_are_not_empty() -> None:
    raw = _corpus_or_skip()
    for directory in raw.iterdir():  # type: ignore[attr-defined]
        for path in directory.glob("*"):
            if path.name == "_provenance.json":
                continue
            assert path.stat().st_size > 500, f"{path} looks like an error page"
