"""Grounded answer generation.

DeepSeek rewrites retrieved agronomy into something a farmer can act on. Two constraints
shape everything here:

**Only what was retrieved.** The model is a rewriter, not a source. Anything it "knows"
about banana disease that is not in the retrieved passages is exactly the kind of confident,
unverifiable claim this system exists to avoid.

**Refusal is a valid answer.** When retrieval comes back weak, the honest response is "I
don't have reliable information on this" — and it has to be, because the alternative is a
fluent paraphrase of whatever was least-bad in the index.

Generation is followed by ``safety.enforce``. The prompt asks for correct behaviour; the
checks verify it. Neither alone is enough.
"""

# E501: several regexes and the refusal strings read worse when wrapped.
# RUF001: the Urdu refusal text legitimately contains an Arabic full stop.
# ruff: noqa: RUF001

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from banana_lifeline.generation import safety

if TYPE_CHECKING:
    from banana_lifeline.rag.retrieve import RetrievalResult

DEFAULT_MODEL = "deepseek-v4-flash"

#: The five sections the app renders. Fixed so the UI can rely on the shape.
SECTIONS = ("what_it_is", "symptoms", "what_to_do", "prevention", "precautions")

_SYSTEM_PROMPT = """You explain plant disease guidance to banana farmers in Pakistan. Many \
have limited formal education and are reading on a phone.

ABSOLUTE RULES:
1. Use ONLY the numbered sources provided. If they do not answer the question, say so \
plainly. Never fill a gap from your own knowledge.
2. Never invent a quantity. Chemical amounts, spray intervals and concentrations may only \
appear if they are written in a source, copied exactly.
3. Panama disease (Fusarium wilt) has NO chemical cure. Never suggest a spray or fungicide \
can cure it. Guidance is containment only.
4. Cite the source number in square brackets after each claim, like [1].

STYLE:
- Short sentences. Everyday words. No jargon without explaining it.
- Say what to DO, in order, not what is theoretically true.
- Never guess at cost or where to buy something.
- If a source is unclear, say the farmer should ask an extension officer.

Answer in {language}."""

_USER_TEMPLATE = """Question: {question}
{diagnosis}
Sources:
{sources}

Write the answer using only these sources."""


@dataclass(slots=True)
class Answer:
    """A generated answer plus everything needed to audit it."""

    text: str
    language: str
    disease: str | None
    citations: list[dict[str, str]] = field(default_factory=list)
    refused: bool = False
    safety_violations: list[str] = field(default_factory=list)
    model: str = DEFAULT_MODEL
    raw_text: str = ""

    @property
    def was_amended(self) -> bool:
        return bool(self.raw_text) and self.raw_text != self.text


REFUSAL_TEXT = {
    "en": "I don't have reliable information about that in my sources. Please ask a local "
    "agricultural extension officer.",
    "ur": "میرے پاس اس بارے میں قابلِ اعتماد معلومات موجود نہیں ہیں۔ براہِ کرم اپنے مقامی "
    "زرعی افسر سے رابطہ کریں۔",
}


def _format_sources(result: RetrievalResult) -> str:
    return "\n\n".join(
        f"[{index}] {passage.citation()}\n{passage.text}"
        for index, passage in enumerate(result.passages, 1)
    )


def generate_answer(
    question: str,
    result: RetrievalResult,
    *,
    disease: str | None = None,
    language: str = "en",
    model: str = DEFAULT_MODEL,
    diagnosis_note: str = "",
) -> Answer:
    """Turn retrieved passages into farmer-facing guidance.

    Refuses outright when retrieval is weak, before spending a token: a model given poor
    context produces a fluent answer built on it, and fluency is precisely what makes that
    dangerous.
    """
    if result.is_weak:
        return Answer(
            text=REFUSAL_TEXT.get(language, REFUSAL_TEXT["en"]),
            language=language,
            disease=disease,
            refused=True,
            model=model,
        )

    from banana_lifeline.generation.client import complete

    # Always generate in English, then translate the approved text. The safety rules are
    # English regexes -- Panama cure claims, ungrounded dosages, missing PPE. Generating
    # straight into Urdu produced an answer that quoted a spray rate with no protective-
    # equipment warning and passed every check, because none of the patterns matched. A
    # safety layer that silently does nothing for half the users is worse than none, since
    # it looks like it is working.
    prompt = _USER_TEMPLATE.format(
        question=question,
        diagnosis=f"\nThe photo was identified as: {disease}.\n" if disease else "",
        sources=_format_sources(result),
    )

    try:
        raw = complete(
            [
                {"role": "system", "content": _SYSTEM_PROMPT.format(language="English")},
                {"role": "user", "content": prompt},
            ],
            model=model,
            temperature=0.2,  # low: this is rewriting, not composition
        )
    except Exception as exc:
        # Retries are exhausted by this point, so this is a real outage rather than a blip.
        return Answer(
            text=REFUSAL_TEXT.get(language, REFUSAL_TEXT["en"]),
            language=language,
            disease=disease,
            refused=True,
            safety_violations=[f"generation unavailable: {exc}"],
            model=model,
        )

    checked = safety.enforce(
        raw,
        disease=disease,
        source_texts=[p.text for p in result.passages],
        source_regions=[p.region for p in result.passages],
    )

    final_text = checked.amended_text
    if language != "en":
        final_text = _translate_answer(final_text, language, model)

    return Answer(
        text=final_text,
        language=language,
        disease=disease,
        citations=[
            {
                "n": str(index),
                "source": passage.source,
                "title": passage.title,
                "url": passage.url,
            }
            for index, passage in enumerate(result.passages, 1)
        ],
        refused=False,
        safety_violations=[f"{v.rule}:{v.severity.value}" for v in checked.violations],
        model=model,
        raw_text=raw,
    )


_TRANSLATE_OUT_PROMPT = """Translate this agricultural advice into {language} for a farmer.

- Keep every number, dose, and interval exactly as written.
- Keep chemical names in Latin script, with the {language} explanation beside them.
- Keep the [1] [2] citation markers exactly where they are.
- Keep all safety warnings. Never drop or soften them.
- Plain, everyday wording."""


def _translate_answer(text: str, language: str, model: str) -> str:
    """Translate an already-safety-checked answer.

    Failure returns the English text rather than nothing: a farmer who reads some English is
    better served than one who gets a refusal for an answer we actually have.
    """
    from banana_lifeline.generation.client import complete

    language_name = {"ur": "Urdu"}.get(language, language)
    try:
        return complete(
            [
                {"role": "system", "content": _TRANSLATE_OUT_PROMPT.format(language=language_name)},
                {"role": "user", "content": text},
            ],
            model=model,
            temperature=0.1,
        )
    except Exception:
        return text


def answer_follow_up(
    responses: dict[str, bool],
    *,
    language: str = "en",
) -> tuple[str, float]:
    """Combine answers to the Panama follow-up questions into a confidence.

    Each sign is weighted by how specific it is. Vascular discolouration inside a cut stem
    is close to definitive; yellowing older leaves alone is shared with potassium deficiency
    and drought, so on its own it means little.

    Returns ``(message, confidence)``.
    """
    weights = {
        "older_leaves_yellow_first": 0.20,
        "leaves_collapse_around_stem": 0.25,
        "brown_lines_inside_stem": 0.40,
        "stem_base_splitting": 0.15,
    }

    score = sum(weight for key, weight in weights.items() if responses.get(key))

    if score >= 0.60:
        message = (
            "These signs together point strongly to Panama disease. There is no chemical "
            "cure, so act to stop it spreading: do not move soil, suckers, or tools away "
            "from this plant, and report it to your agricultural extension office."
        )
    elif score >= 0.30:
        message = (
            "Some signs match Panama disease, but not enough to be sure. Please show the "
            "plant to an agricultural extension officer before removing anything."
        )
    else:
        message = (
            "These signs do not match Panama disease well. The yellowing may have another "
            "cause, such as a nutrient shortage or waterlogging. An extension officer can "
            "check the plant."
        )

    return message, score
