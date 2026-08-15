"""Tests for query translation.

Translation sits between a farmer's question and everything else. If it silently mangles a
symptom, retrieval fetches the wrong disease and the answer that follows is fluent, cited,
and wrong — the most dangerous failure this system can produce. These tests cover the parts
that can be checked without calling DeepSeek.
"""

from __future__ import annotations

from banana_lifeline.rag.translate import (
    GLOSSARY,
    TranslatedQuery,
    apply_glossary,
    detect_language,
    translate_query,
)

# --------------------------------------------------------------------------------------
# Language detection
# --------------------------------------------------------------------------------------


def test_urdu_script_is_detected() -> None:
    assert detect_language("کیلے کے پتوں پر پیلے دھبے ہیں") == "ur"


def test_english_is_detected() -> None:
    assert detect_language("My banana leaves have yellow spots") == "en"


def test_roman_urdu_reads_as_english() -> None:
    """Roman Urdu is Latin script, so script detection cannot catch it.

    That is a known limitation, not an oversight: Roman Urdu is deferred, and DeepSeek's
    translation prompt is a no-op on text it considers already-English. Worth a test so the
    behaviour is recorded rather than discovered later.
    """
    assert detect_language("kelay ke patton par peele dhabbe hain") == "en"


def test_mostly_english_with_one_urdu_word_stays_english() -> None:
    assert detect_language("What is پاناما disease and how do I treat it properly") == "en"


# --------------------------------------------------------------------------------------
# Glossary
# --------------------------------------------------------------------------------------


def test_glossary_maps_to_corpus_vocabulary() -> None:
    """ "مرجھاؤ" is conversationally "withering"; the manuals say "wilt".

    A correct-sounding translation that uses the wrong synonym still misses the index.
    """
    assert GLOSSARY["مرجھاؤ"] == "wilt"
    assert GLOSSARY["تنا"] == "pseudostem"
    assert GLOSSARY["پاناما"] == "Panama disease"


def test_glossary_substitution_produces_searchable_english() -> None:
    result = apply_glossary("کیلے کے پتوں پر پیلے دھبے")
    assert "banana" in result
    assert "leaves" in result
    assert "yellow" in result
    assert "spots" in result


def test_glossary_output_has_no_double_spaces() -> None:
    assert "  " not in apply_glossary("کیلے کے پتے پیلے")


def test_glossary_covers_both_diseases() -> None:
    """Retrieval filters on disease, so the disease names must survive translation."""
    values = " ".join(GLOSSARY.values()).lower()
    assert "panama" in values
    assert "sigatoka" in values


# --------------------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------------------


def test_english_queries_are_not_sent_for_translation() -> None:
    """No API call, no latency, no chance of a model rewriting a question that was fine."""
    result = translate_query("How do I treat black sigatoka?")
    assert result.was_translated is False
    assert result.translated == result.original
    assert result.source_language == "en"


def test_translation_can_be_disabled() -> None:
    result = translate_query("کیلے کی بیماری", enabled=False)
    assert result.was_translated is False
    assert result.translated == result.original


def test_failure_falls_back_to_the_glossary() -> None:
    """A partly translated query still retrieves something.

    Raising instead would lose the farmer's question entirely, which is strictly worse than
    searching on the handful of terms the glossary can resolve without a model.
    """
    import banana_lifeline.rag.translate as module

    original = module._translate_via_deepseek
    module._translate_via_deepseek = lambda *_, **__: (_ for _ in ()).throw(RuntimeError("down"))
    try:
        result = translate_query("کیلے کے پتوں پر دھبے")
    finally:
        module._translate_via_deepseek = original

    assert "banana" in result.translated
    assert "spots" in result.translated


# --------------------------------------------------------------------------------------
# Auditability
# --------------------------------------------------------------------------------------


def test_audit_line_shows_both_forms_of_a_translated_query() -> None:
    """When an answer is wrong, the first question is whether the translation was."""
    translated = TranslatedQuery(
        original="کیلے کی بیماری",
        translated="banana disease",
        source_language="ur",
        was_translated=True,
    )
    line = translated.audit_line

    assert "کیلے کی بیماری" in line
    assert "banana disease" in line


def test_audit_line_stays_quiet_for_untranslated_queries() -> None:
    plain = TranslatedQuery("soil type?", "soil type?", "en", was_translated=False)
    assert "->" not in plain.audit_line


def test_fallback_records_why_it_degraded() -> None:
    """Silent degradation is the bug this guards against.

    A transient API failure used to fall back to the glossary with no signal anywhere: the
    half-translated query still retrieved passages, generation still ran, and the answer
    still looked fine. Nothing distinguished it from a successful translation.
    """
    import banana_lifeline.rag.translate as module

    original = module._translate_via_deepseek
    module._translate_via_deepseek = lambda *_, **__: (_ for _ in ()).throw(RuntimeError("down"))
    try:
        result = translate_query("کیلے کے پتوں پر دھبے")
    finally:
        module._translate_via_deepseek = original

    assert result.degraded
    assert "RuntimeError" in result.fallback_reason
    assert "GLOSSARY FALLBACK" in result.audit_line


def test_an_empty_translation_also_counts_as_degraded() -> None:
    import banana_lifeline.rag.translate as module

    original = module._translate_via_deepseek
    module._translate_via_deepseek = lambda *_, **__: ""
    try:
        result = translate_query("کیلے کی بیماری")
    finally:
        module._translate_via_deepseek = original

    assert result.degraded
    assert "empty" in result.fallback_reason


def test_a_successful_translation_is_not_marked_degraded() -> None:
    import banana_lifeline.rag.translate as module

    original = module._translate_via_deepseek
    module._translate_via_deepseek = lambda *_, **__: "black spots on banana leaves"
    try:
        result = translate_query("کیلے کے پتوں پر کالے دھبے")
    finally:
        module._translate_via_deepseek = original

    assert not result.degraded
    assert result.was_translated
