"""Tests for chunking, classification, fusion, and the evaluation harness.

None of these need a network, a model, or a live Qdrant. Retrieval is exercised through
injected fakes so the logic that decides *what a farmer is told* stays covered in CI, where
no vector database exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from banana_lifeline.rag.chunk import (
    Chunk,
    _split_sections,
    build_context_prefix,
    chunk_document,
    estimate_tokens,
)
from banana_lifeline.rag.classify import classify_disease, classify_topic
from banana_lifeline.rag.eval import GoldenQuestion, _ndcg, evaluate_retrieval
from banana_lifeline.rag.retrieve import reciprocal_rank_fusion

# --------------------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------------------


def test_sections_split_on_headings() -> None:
    text = "intro paragraph\n\n## Symptoms\n\nyellow leaves\n\n## Control\n\nspray weekly"
    sections = _split_sections(text)

    assert [path for path, _ in sections] == [[], ["Symptoms"], ["Control"]]
    assert "yellow leaves" in sections[1][1]


def test_preamble_is_kept_not_discarded() -> None:
    """Text before the first heading is usually the document's summary.

    It is often the single most useful passage in the file, so dropping it is expensive.
    """
    sections = _split_sections("This guide covers Panama disease.\n\n## Details\n\nbody")
    assert sections[0][0] == []
    assert "This guide covers" in sections[0][1]


def test_document_title_travels_onto_every_chunk() -> None:
    """A multi-file source shares one registry title, so the chapter is otherwise lost.

    Hawaii's guidebook is 14 chapters under one title; without this, chunks from the
    Panama chapter carry no hint of their subject and classify as `general`.
    """
    text = (
        "## Fusarium Wilt or Panama Disease\n\n"
        + ("The pathogen survives in soil for decades. " * 30)
        + "\n\n## Management\n\n"
        + ("Use clean planting material. " * 30)
    )
    chunks = chunk_document(
        text, {"slug": "hawaii", "title": "Guidebook", "source": "UH"}, filename="CHPT2-Panama"
    )

    assert chunks
    assert all("Fusarium Wilt or Panama Disease" in c.heading_path for c in chunks)


def test_long_sections_split_with_overlap() -> None:
    body = "## S\n\n" + " ".join(f"Sentence number {i} about sigatoka control." for i in range(300))
    chunks = chunk_document(body, {"slug": "x", "title": "T", "source": "S"}, filename="f.txt")

    assert len(chunks) > 1
    assert all(c.n_tokens <= 700 for c in chunks)


def test_tiny_fragments_are_dropped() -> None:
    """Stray captions and orphan headings are noise in a retrieval index."""
    chunks = chunk_document(
        "## A\n\nshort\n\n## B\n\nalso short",
        {"slug": "x", "title": "T", "source": "S"},
        filename="f.txt",
    )
    assert chunks == []


def test_context_prefix_names_document_and_section() -> None:
    """Retrieved alone, "apply the second treatment" is unusable without this."""
    prefix = build_context_prefix("Fusarium Manual", "FAO", ["Chapter 4", "Soil management"])
    assert "FAO" in prefix and "Fusarium Manual" in prefix and "Soil management" in prefix


def test_embedding_text_includes_the_prefix() -> None:
    chunk = Chunk(
        chunk_id="c",
        text="body",
        context_prefix="From FAO's manual, section: X.",
        slug="s",
        source="FAO",
        title="T",
        url="",
        authority="international",
        region="global",
        document_type="technical_manual",
        language="en",
        year=2015,
        licence="",
    )
    assert chunk.embedding_text.startswith("From FAO")
    assert "body" in chunk.embedding_text


def test_token_estimate_is_monotonic() -> None:
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 100)


# --------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------


def test_diagnostic_terms_beat_generic_ones() -> None:
    """ "Fusarium oxysporum" can only be Panama; "wilt" alone means little."""
    assert (
        classify_disease("Fusarium oxysporum f. sp. cubense infects the roots", [], ()) == "panama"
    )
    assert (
        classify_disease("Mycosphaerella fijiensis causes black leaf streak", [], ()) == "sigatoka"
    )


def test_headings_outweigh_body_text() -> None:
    """A passage under "Fusarium wilt" is about Panama even if it only says "the disease"."""
    assert (
        classify_disease("The disease spreads quickly.", ["Fusarium wilt of banana"], ())
        == "panama"
    )


def test_single_disease_document_resolves_ambiguity() -> None:
    """A chunk in an FAO Fusarium manual is about Panama whatever else it mentions."""
    assert classify_disease("Remove and destroy affected plants.", [], ("panama",)) == "panama"


def test_ambiguous_multi_disease_chunk_stays_general() -> None:
    """Filing a chunk under the wrong disease is worse than filing it under none.

    The filter would surface it confidently for a question it cannot answer.
    """
    text = "Both Panama disease and black sigatoka affect banana production worldwide."
    assert classify_disease(text, [], ("panama", "sigatoka", "general")) == "general"


def test_topics_are_assigned_from_intent_not_mention() -> None:
    assert classify_topic("Apply fungicide at a rate of 2 litres per hectare", []) == "treatment"
    assert classify_topic("Wear protective clothing and a mask when spraying", []) == "precautions"
    assert classify_topic("Space plants three metres apart in fertile loam", []) == "cultivation"
    assert classify_topic("The first symptom is yellowing of older leaves", []) == "symptoms"


# --------------------------------------------------------------------------------------
# Rank fusion
# --------------------------------------------------------------------------------------


@dataclass
class _Point:
    id: str
    payload: dict[str, object] = field(default_factory=dict)


def test_fusion_rewards_agreement_between_rankings() -> None:
    """A passage both searches rank highly should beat one only either found."""
    dense = [_Point("a"), _Point("b"), _Point("c")]
    sparse = [_Point("c"), _Point("a"), _Point("d")]

    fused = reciprocal_rank_fusion([dense, sparse])
    assert fused[0][0].id == "a"


def test_fusion_uses_rank_not_score() -> None:
    """Dense cosine and sparse lexical scores are not comparable; normalising is guesswork."""
    only_dense = reciprocal_rank_fusion([[_Point("x"), _Point("y")]])
    assert [p.id for p, _ in only_dense] == ["x", "y"]


def test_fusion_of_nothing_is_empty() -> None:
    assert reciprocal_rank_fusion([]) == []


# --------------------------------------------------------------------------------------
# Evaluation harness
# --------------------------------------------------------------------------------------


@dataclass
class _Passage:
    text: str
    source: str = "FAO"
    chunk_id: str = "fao_fusarium_wilt_manual__x__000_00"


@dataclass
class _Result:
    passages: list[_Passage]

    @property
    def is_empty(self) -> bool:
        return not self.passages

    @property
    def best_score(self) -> float:
        return 0.8 if self.passages else 0.0

    @property
    def is_weak(self) -> bool:
        return self.is_empty


def test_ndcg_rewards_putting_the_answer_first() -> None:
    assert _ndcg([1, 0, 0]) > _ndcg([0, 0, 1])
    assert _ndcg([0, 0, 0]) == 0.0


def test_perfect_retrieval_scores_one() -> None:
    questions = [
        GoldenQuestion(
            question="q",
            language="en",
            disease=None,
            topic=None,
            expect_terms=["vascular discolouration"],
        )
    ]
    report = evaluate_retrieval(
        questions, lambda *_: _Result([_Passage("shows vascular discolouration inside")])
    )
    assert report.recall_at_1 == 1.0
    assert report.mrr == 1.0


def test_refusal_is_scored_separately_from_recall() -> None:
    """Without this, metrics reward a system that always returns its best guess.

    In agriculture that guess becomes a spray recommendation someone acts on.
    """
    questions = [
        GoldenQuestion(
            question="banana price?", language="en", disease=None, topic=None, unanswerable=True
        )
    ]

    refused = evaluate_retrieval(questions, lambda *_: _Result([]))
    assert refused.refusal_accuracy == 1.0

    answered = evaluate_retrieval(questions, lambda *_: _Result([_Passage("irrelevant text")]))
    assert answered.refusal_accuracy == 0.0


def test_unanswerable_questions_do_not_dilute_recall() -> None:
    questions = [
        GoldenQuestion(
            question="a", language="en", disease=None, topic=None, expect_terms=["found"]
        ),
        GoldenQuestion(question="b", language="en", disease=None, topic=None, unanswerable=True),
    ]
    report = evaluate_retrieval(questions, lambda q, *_: _Result([_Passage("found it")]))

    assert report.recall_at_1 == 1.0  # scored over the one answerable question only
    assert report.refusal_accuracy == 0.0


def test_source_match_counts_as_relevant() -> None:
    questions = [
        GoldenQuestion(
            question="q",
            language="en",
            disease=None,
            topic=None,
            expect_terms=["nothing matches this"],
            expect_sources=["fao_fusarium_wilt_manual"],
        )
    ]
    report = evaluate_retrieval(questions, lambda *_: _Result([_Passage("unrelated wording")]))
    assert report.recall_at_1 == 1.0


# --------------------------------------------------------------------------------------
# Golden set integrity
# --------------------------------------------------------------------------------------


def test_golden_set_covers_both_languages_and_refusal() -> None:
    from banana_lifeline.rag.golden import GOLDEN_SET

    languages = {q.language for q in GOLDEN_SET}
    assert {"en", "ur"} <= languages, "Urdu must be tested from the start, not retrofitted"
    assert sum(1 for q in GOLDEN_SET if q.unanswerable) >= 3


def test_golden_questions_are_well_formed() -> None:
    from banana_lifeline.rag.golden import GOLDEN_SET

    for question in GOLDEN_SET:
        assert question.question.strip()
        if question.unanswerable:
            assert not question.expect_terms, "an unanswerable question expects nothing"
        else:
            assert question.expect_terms or question.expect_sources


def test_golden_set_covers_every_disease() -> None:
    from banana_lifeline.rag.golden import GOLDEN_SET

    covered = {q.disease for q in GOLDEN_SET}
    assert "panama" in covered and "sigatoka" in covered and None in covered


def test_panama_has_a_no_cure_question() -> None:
    """The hard safety rule needs a retrieval test behind it.

    If retrieval cannot surface the "no chemical cure" material, generation has nothing
    truthful to ground that answer in.
    """
    from banana_lifeline.rag.golden import GOLDEN_SET

    matches = [
        q
        for q in GOLDEN_SET
        if q.disease == "panama" and any("cure" in t or "chemical" in t for t in q.expect_terms)
    ]
    assert matches, "no golden question checks the 'Panama has no cure' material"
