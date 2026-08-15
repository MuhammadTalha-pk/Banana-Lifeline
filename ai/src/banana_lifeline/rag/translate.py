"""Query translation.

The corpus is English; farmers ask in Urdu. Rather than asking the embedder to bridge that
gap, DeepSeek translates the question into English before retrieval and answers in the
farmer's language afterwards. That lets retrieval use the strongest English model available
instead of paying a multilingual quality tax.

The cost is a new failure mode: a mistranslated symptom retrieves the wrong disease, and the
answer that follows is fluent, sourced, and wrong. Two things guard against it.

**Translation is logged.** Every translated query is returned alongside the original, so a
bad answer can be traced to a bad translation rather than blamed on retrieval.

**Domain terms are pinned.** A general model translating agricultural Urdu will render
"مرجھاؤ" as "withering" where the corpus says "wilt", and the retrieval misses. The glossary
below fixes the vocabulary that actually decides which disease gets retrieved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

#: Urdu agricultural terms mapped to the wording the corpus actually uses. Without this a
#: correct-sounding translation can still miss, because "leaf blight" and "leaf spot" are
#: interchangeable in conversation and are not interchangeable in a search index.
GLOSSARY: dict[str, str] = {
    "کیلا": "banana",
    "کیلے": "banana",
    "پتہ": "leaf",
    "پتے": "leaves",
    "پتوں": "leaves",
    "بیماری": "disease",
    "پیلا": "yellow",
    "پیلے": "yellow",
    "دھبے": "spots",
    "دھبہ": "spot",
    "لکیریں": "streaks",
    "مرجھاؤ": "wilt",
    "تنا": "pseudostem",
    "جڑ": "root",
    "پھپھوندی": "fungus",
    "دوا": "pesticide",
    "سپرے": "spray",
    "مٹی": "soil",
    "پانی": "irrigation",
    "کھاد": "fertiliser",
    "فصل": "crop",
    "پودا": "plant",
    "پودے": "plants",
    "علاج": "treatment",
    "روک تھام": "prevention",
    "پاناما": "Panama disease",
    "سگاٹوکا": "Sigatoka",
}

_URDU_RANGE = re.compile(r"[؀-ۿݐ-ݿ]")

_SYSTEM_PROMPT = """You translate a farmer's question about banana cultivation into English \
so it can be searched against agricultural manuals.

Rules:
- Output ONLY the translated question. No commentary, no quotes, no explanation.
- Use the technical vocabulary agricultural manuals use, not conversational wording:
  "wilt" not "withering", "lesion" or "spot" not "mark", "pseudostem" not "trunk".
- Keep every symptom detail. Which leaves, what colour, where on the plant, and how it \
progresses are exactly what distinguishes one disease from another.
- Never diagnose. Translate the question that was asked; do not answer it or name a disease \
the farmer did not name.
- If the text is already English, return it unchanged."""


@dataclass(slots=True)
class TranslatedQuery:
    """A query as asked and as searched, so the two can be compared when an answer is wrong."""

    original: str
    translated: str
    source_language: str
    was_translated: bool

    #: Set when translation degraded to the offline glossary. A transient API failure used
    #: to be swallowed silently, leaving a half-Urdu query that still "worked" -- retrieval
    #: returned something, generation ran, and nothing anywhere said the translation had
    #: failed. Degradation has to be visible or it is indistinguishable from success.
    fallback_reason: str = ""

    @property
    def degraded(self) -> bool:
        return bool(self.fallback_reason)

    @property
    def audit_line(self) -> str:
        if self.fallback_reason:
            return (
                f"query ({self.source_language}): {self.original!r} -> GLOSSARY FALLBACK "
                f"{self.translated!r} ({self.fallback_reason})"
            )
        if not self.was_translated:
            return f"query ({self.source_language}): {self.original}"
        return (
            f"query ({self.source_language}): {self.original!r} -> searched as: {self.translated!r}"
        )


def detect_language(text: str) -> str:
    """Crude script detection: Urdu and Arabic share a Unicode block, Roman Urdu looks Latin.

    Good enough for routing, because the translation prompt is a no-op on English input.
    """
    urdu_chars = len(_URDU_RANGE.findall(text))
    return "ur" if urdu_chars >= max(2, len(text.replace(" ", "")) * 0.2) else "en"


def apply_glossary(text: str) -> str:
    """Substitute pinned domain terms before the model sees the text."""
    result = text
    for urdu, english in GLOSSARY.items():
        result = result.replace(urdu, f" {english} ")
    return re.sub(r"\s+", " ", result).strip()


@lru_cache(maxsize=256)
def _translate_via_deepseek(text: str, model: str) -> str:
    """Translate one query. Retries transient API failures before giving up."""
    from banana_lifeline.generation.client import complete

    return complete(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        model=model,
        temperature=0,  # translation must be reproducible; the eval depends on it
        # 200 was far too low. This model reasons before answering and those tokens count
        # against the budget, so a short translation came back as the truncated fragment
        # "There are" -- which then retrieved nothing at all (similarity 0.048).
        max_tokens=2000,
        timeout=60,
    )


def translate_query(
    text: str,
    *,
    model: str = "deepseek-v4-flash",
    enabled: bool = True,
) -> TranslatedQuery:
    """Translate a question into English for retrieval.

    Falls back to the glossary substitution alone when DeepSeek is unreachable — a partly
    translated query still retrieves something useful, whereas an exception loses the
    farmer's question entirely.
    """
    language = detect_language(text)

    if language == "en" or not enabled:
        return TranslatedQuery(text, text, language, was_translated=False)

    reason = ""
    try:
        translated = _translate_via_deepseek(text, model)
        if translated:
            return TranslatedQuery(text, translated, language, was_translated=True)
        reason = "translation model returned an empty response"
    except Exception as exc:
        reason = f"translation failed: {type(exc).__name__}"

    fallback = apply_glossary(text)
    return TranslatedQuery(
        text,
        fallback or text,
        language,
        was_translated=bool(fallback),
        fallback_reason=reason,
    )
