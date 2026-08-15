"""Tests for intent routing.

The router decides whether a message reaches the knowledge base at all, so its two failure
directions are not equally bad and the tests are weighted accordingly.

Routing a real question to a greeting means a farmer with a dying crop is told "hello, how
can I help?" — the failure this system exists to prevent. Routing a greeting into retrieval
costs one wasted search that refuses. Most of what follows therefore checks that questions
survive routing, including under every way the model call can fail.
"""

# RUF001: the Urdu test fixtures legitimately contain Arabic-script punctuation.
# ruff: noqa: RUF001

from __future__ import annotations

import pytest

from banana_lifeline.generation.intent import (
    Intent,
    _parse,
    classify,
    greeting_text,
    looks_like_greeting,
    looks_technical,
    names_other_subject,
    normalise,
    out_of_scope_text,
)

# --------------------------------------------------------------------------------------
# Greetings — the case that started this
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "hi",
        "Hi!",
        "hello",
        "Hello there",
        "hey",
        "good morning",
        "How are you?",
        "thanks",
        "Thank you so much",
        "bye",
        "ok",
        "assalam o alaikum",
        "AOA",
        "shukriya",
        "السلام علیکم",
        "شکریہ",
    ],
)
def test_greetings_never_reach_retrieval(message: str) -> None:
    """"hi" used to return five passages on plantation renewal cycles."""
    assert classify(message, use_model=False).intent is Intent.GREETING


def test_greeting_routing_costs_no_api_call() -> None:
    """Every greeting must resolve on the rule path.

    ``use_model=False`` makes an un-matched greeting fall through to TECHNICAL, so this
    passing is proof the rules caught it rather than the model.
    """
    result = classify("hello", use_model=False)
    assert result.used_model is False
    assert result.intent is Intent.GREETING


def test_an_empty_message_is_not_a_query() -> None:
    assert classify("   ", use_model=False).intent is Intent.GREETING


# --------------------------------------------------------------------------------------
# Questions about the assistant itself
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "can you help me",
        "Can you help?",
        "what can you do",
        "who are you",
        "what is your name",
        "what is this",
        "how does this work",
        "help",
        "آپ کون ہیں",
    ],
)
def test_meta_questions_get_the_capability_reply(message: str) -> None:
    """The model routed these to out_of_scope, which was actively wrong.

    Someone typing "can you help me" was answered "I only know about bananas -- I cannot
    help with that." They are asking to be helped, not asking about an unrelated topic, and
    the greeting already says what the system can do.
    """
    assert classify(message, use_model=False).intent is Intent.GREETING


def test_meta_questions_cost_no_api_call() -> None:
    assert classify("what can you do", use_model=False).used_model is False


def test_a_meta_phrase_carrying_a_real_question_is_still_technical() -> None:
    """Exact-phrase matching only, so the offer of help does not swallow the question."""
    assert classify("can you help me with my banana leaves", use_model=False).intent is (
        Intent.TECHNICAL
    )


# --------------------------------------------------------------------------------------
# Questions must survive routing — the direction that actually matters
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "my banana leaves are turning yellow",
        "how far apart should I plant them",
        "what soil is best",
        "when should I water",
        "hi, my leaves have dark streaks",  # opens with a greeting, is not one
        "hello can you tell me about panama disease",
        "thanks, but what about the spray dose",
        "کیلے کے پتوں پر پیلے دھبے ہیں",
        "مٹی کون سی بہترین ہے",
    ],
)
def test_real_questions_reach_retrieval(message: str) -> None:
    assert classify(message, use_model=False).intent is Intent.TECHNICAL


def test_a_greeting_prefix_does_not_swallow_the_question() -> None:
    """The all-tokens rule is what makes the greeting fast path safe."""
    assert looks_like_greeting("hi") is True
    assert looks_like_greeting("hi my leaves are yellow") is False


def test_a_long_message_of_filler_words_is_not_a_greeting() -> None:
    """Real greetings are short. An unbounded token check would misread a rambling one."""
    assert looks_like_greeting("ok ok ok sure sure sure ok please") is False


def test_urdu_questions_are_recognised_without_translation() -> None:
    """Routing runs before translation, so it must read Urdu script directly."""
    assert looks_technical("کیلے کی بیماری") is True
    assert looks_technical("السلام علیکم") is False


# --------------------------------------------------------------------------------------
# Every uncertain path resolves to TECHNICAL
# --------------------------------------------------------------------------------------


def _with_router(monkeypatch: pytest.MonkeyPatch, replacement: object) -> None:
    import banana_lifeline.generation.intent as module

    module._classify_via_deepseek.cache_clear()
    monkeypatch.setattr(module, "_classify_via_deepseek", replacement)


def test_a_routing_outage_sends_the_message_to_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retrieval refuses safely. A skipped question does not."""

    def boom(*_: object, **__: object) -> str:
        raise RuntimeError("deepseek down")

    _with_router(monkeypatch, boom)
    result = classify("tell me more")

    assert result.intent is Intent.TECHNICAL
    assert "RuntimeError" in result.reason


def test_an_unreadable_reply_sends_the_message_to_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_router(monkeypatch, lambda *_, **__: "well, it could be a greeting or technical")
    assert classify("tell me more").intent is Intent.TECHNICAL


def test_an_empty_reply_sends_the_message_to_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_router(monkeypatch, lambda *_, **__: "")
    assert classify("tell me more").intent is Intent.TECHNICAL


def test_disabling_the_model_leaves_ambiguous_messages_technical() -> None:
    result = classify("tell me more", use_model=False)
    assert result.intent is Intent.TECHNICAL
    assert result.used_model is False


def test_the_model_can_route_the_genuinely_ambiguous(monkeypatch: pytest.MonkeyPatch) -> None:
    _with_router(monkeypatch, lambda *_, **__: "out_of_scope")
    result = classify("who won the cricket world cup")

    assert result.intent is Intent.OUT_OF_SCOPE
    assert result.used_model is True


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("greeting", Intent.GREETING),
        ("technical", Intent.TECHNICAL),
        ("out_of_scope", Intent.OUT_OF_SCOPE),
        ("  Technical.  ", Intent.TECHNICAL),
        ("greeting technical", None),  # named two, so it named none
        ("banana", None),
    ],
)
def test_reply_parsing(reply: str, expected: Intent | None) -> None:
    assert _parse(reply) == expected


# --------------------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------------------


def test_punctuation_is_stripped_in_both_scripts() -> None:
    assert normalise("Hi!!!") == "hi"
    assert normalise("hello... there?") == "hello there"
    assert normalise("السلام علیکم۔") == "السلام علیکم"


# --------------------------------------------------------------------------------------
# What the farmer is actually shown
# --------------------------------------------------------------------------------------


def test_the_greeting_says_what_the_system_can_do() -> None:
    """A bare "hello" wastes the farmer's turn. It has to offer the two entry points."""
    text = greeting_text("en")
    assert "photo" in text.lower()
    assert "sigatoka" in text.lower()


def test_the_greeting_carries_the_diagnosis_forward() -> None:
    """Forgetting the photo it was just shown would make the assistant look broken."""
    assert "sigatoka" in greeting_text("en", disease="sigatoka").lower()
    assert "healthy" in greeting_text("en", disease="healthy").lower()


@pytest.mark.parametrize("language", ["en", "ur"])
def test_the_greeting_claims_no_photo_when_there_is_none(language: str) -> None:
    """The counterpart to the test above, and the one that caught a real bug.

    A farmer who had sent no photo was told "Your photo looked healthy", because the app
    held a diagnosis in session state that nothing ever cleared. The reply must not mention
    a photo unless one was actually passed in.
    """
    text = greeting_text(language)
    photo_word = "photo" if language == "en" else "تصویر"
    assert "healthy" not in text.lower()
    assert text.count(photo_word) == 1  # the offer to send one, nothing more


def test_the_greeting_is_translated() -> None:
    assert greeting_text("ur") != greeting_text("en")
    assert "سگاٹوکا" in greeting_text("ur")


def test_an_unknown_language_falls_back_to_english() -> None:
    assert greeting_text("fr") == greeting_text("en")
    assert out_of_scope_text("fr") == out_of_scope_text("en")


def test_the_refusal_redirects_rather_than_just_declining() -> None:
    text = out_of_scope_text("en")
    assert "banana" in text.lower()
    assert "soil" in text.lower()


# --------------------------------------------------------------------------------------
# Other subjects — farming, but not this corpus
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "What fertiliser dose should I apply to my wheat crop?",
        "How do I treat foot and mouth disease in my cattle?",
        "Which bank gives the best agricultural loan in Punjab?",
        "What is the current market price of bananas in Lahore?",
        "کیلے کی آج کی قیمت کیا ہے؟",
        "گندم کے لیے کھاد",
    ],
)
def test_other_subjects_leave_the_rule_fast_path(message: str) -> None:
    """These are full of farming words and have no answer in a banana corpus.

    A keyword scan cannot tell "fertiliser for my wheat" from "fertiliser for my bananas",
    so naming another crop, animal, or market topic sends the message to the model instead
    of fast-pathing it to technical.
    """
    assert names_other_subject(message) is True
    assert looks_technical(message) is False


@pytest.mark.parametrize(
    "message",
    [
        "what fertiliser should I use on my bananas",
        "کیلے کے پتوں پر پیلے دھبے ہیں",
        "my banana leaves have yellow spots",
    ],
)
def test_banana_questions_keep_the_fast_path(message: str) -> None:
    assert names_other_subject(message) is False
    assert looks_technical(message) is True


def test_crop_context_is_not_added_to_another_crops_question() -> None:
    """The regression this guards against halved refusal accuracy once already.

    Appending "(banana cultivation)" to a wheat question turned it into a banana question,
    which then retrieved banana passages and scored as answerable.
    """
    from banana_lifeline.rag.retrieve import add_crop_context

    wheat = "What fertiliser dose should I apply to my wheat crop?"
    assert add_crop_context(wheat) == wheat
    assert add_crop_context("when should i water") != "when should i water"
