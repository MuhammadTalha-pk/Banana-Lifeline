"""Assign ``disease`` and ``topic`` metadata to each chunk.

These two fields drive the retrieval filter, which is this system's biggest precision
advantage: the CNN has already named the disease before anything is searched.

Classification is **rule-based on purpose**. Scoring keywords is deterministic, free,
instant, and auditable — when a chunk lands under the wrong disease you can read the rule
that put it there. An LLM pass would be none of those, and on a vocabulary this fixed
(a handful of pathogens and a handful of management topics) it would not classify better.

The one place rules genuinely struggle is a chunk mentioning two diseases in passing. Those
are resolved by score margin, and anything still ambiguous is left as ``general`` rather
than guessed — a chunk filed under the wrong disease is worse than one filed under none,
because the filter would surface it confidently for the wrong question.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from banana_lifeline.rag.chunk import Chunk

PANAMA = "panama"
SIGATOKA = "sigatoka"
GENERAL = "general"

TOPICS = ("symptoms", "cause", "treatment", "prevention", "precautions", "cultivation", "general")

#: Weighted disease vocabulary. Higher weights are terms that are diagnostic on their own:
#: "Fusarium oxysporum" can only be Panama, whereas "wilt" alone means little.
_DISEASE_TERMS: dict[str, dict[str, int]] = {
    PANAMA: {
        r"panama disease": 5,
        r"fusarium wilt": 5,
        r"fusarium oxysporum": 5,
        r"\bfoc\b": 4,
        r"tropical race 4": 5,
        r"\btr4\b": 5,
        r"\brace 1\b": 3,
        r"vascular discolou?ration": 3,
        r"pseudostem splitting": 3,
        r"\bfusarium\b": 2,
        r"wilt": 1,
    },
    SIGATOKA: {
        r"black sigatoka": 5,
        r"yellow sigatoka": 5,
        r"\bsigatoka\b": 4,
        r"mycosphaerella fijiensis": 5,
        r"mycosphaerella musicola": 5,
        r"pseudocercospora": 4,
        r"black leaf streak": 5,
        r"leaf spot": 2,
        r"leaf streak": 2,
        r"defoliation": 1,
    },
}

#: Topic vocabulary. Ordered by specificity when scores tie.
_TOPIC_TERMS: dict[str, dict[str, int]] = {
    "symptoms": {
        r"symptom": 4,
        r"sign of": 2,
        r"appears? as": 2,
        r"first indication": 3,
        r"yellowing": 2,
        r"discolou?ration": 2,
        r"lesion": 2,
        r"diagnos": 3,
        r"identif(y|ication)": 2,
        r"visible": 1,
    },
    "cause": {
        r"caus(e|ed|al agent)": 4,
        r"pathogen": 3,
        r"aetiolog|etiolog": 4,
        r"life cycle": 3,
        r"spread(s)? (by|through)": 3,
        r"transmi(t|ssion)": 3,
        r"infect(s|ion)": 2,
        r"host range": 3,
        r"epidemiolog": 4,
    },
    "treatment": {
        r"treatment": 4,
        r"control measure": 4,
        r"fungicide": 4,
        r"spray": 3,
        r"appl(y|ication) rate": 4,
        r"dosage|dose": 4,
        r"chemical control": 5,
        r"manage(ment)? of": 2,
        r"eradicat": 3,
        r"curative": 3,
    },
    "prevention": {
        r"prevent": 4,
        r"quarantine": 4,
        r"sanitation": 4,
        r"disinfect|steril": 4,
        r"resistant (cultivar|variet)": 5,
        r"exclusion": 3,
        r"clean planting material": 5,
        r"biosecurity": 5,
        r"crop rotation": 3,
        r"avoid": 1,
    },
    "precautions": {
        r"precaution": 5,
        r"protective (equipment|clothing)": 5,
        r"\bppe\b": 5,
        r"safety": 3,
        r"pre-?harvest interval": 5,
        r"toxic": 3,
        r"hazard": 3,
        r"do not": 2,
        r"warning": 3,
        r"restricted": 3,
    },
    "cultivation": {
        # Stems, not exact words. "Space plants three metres apart" matched none of the
        # earlier vocabulary ("spacing", "planting", "soil type") and fell through to
        # `general` -- the words a farmer writes are rarely the words a manual's index uses.
        # Deliberately not a bare "plant": that word appears in every banana document,
        # including "the plant is infected", and swept 46% of the corpus into cultivation.
        r"planting material|plant(ing)? density|plant(ing)? spacing|replant": 4,
        r"irrigat": 4,
        r"fertilis|fertiliz": 4,
        r"\bsoil\b": 3,
        r"spac(e|ed|ing)": 4,
        r"metres? apart|meters? apart": 4,
        r"harvest": 3,
        r"propagat": 4,
        r"sucker": 3,
        r"desucker": 4,
        r"mulch": 3,
        r"drainage": 3,
        r"nutrient": 3,
        r"\bloam\b|fertile": 3,
        r"density": 3,
    },
}

#: A winner must beat the runner-up by this much, or the chunk stays ``general``.
_MIN_MARGIN = 2


@dataclass(slots=True)
class ClassificationStats:
    disease_counts: Counter[str]
    topic_counts: Counter[str]
    ambiguous_disease: int
    n_chunks: int


def _score(text: str, vocabulary: dict[str, int]) -> int:
    """Sum pattern weights, counting each span of text only once.

    Naive summing double-counts nested vocabulary: "black sigatoka" matches both the
    specific pattern (weight 5) and the generic ``\\bsigatoka\\b`` (weight 4), scoring 9 for
    one phrase. That inflation let a chunk mentioning both diseases evenly get classified
    as one of them, defeating the deliberate "stay general when ambiguous" rule.

    So overlapping matches are resolved greedily in favour of the more specific pattern.
    """
    lowered = text.lower()

    spans: list[tuple[int, int, int]] = []
    for pattern, weight in vocabulary.items():
        for match in re.finditer(pattern, lowered):
            spans.append((weight, match.start(), match.end()))

    spans.sort(key=lambda item: (-item[0], item[1]))

    total = 0
    claimed: list[tuple[int, int]] = []
    for weight, start, end in spans:
        if any(start < taken_end and end > taken_start for taken_start, taken_end in claimed):
            continue
        claimed.append((start, end))
        total += weight

    return total


def classify_disease(text: str, heading_path: list[str], declared: tuple[str, ...]) -> str:
    """Pick the disease a chunk is about.

    Headings count double: a passage sitting under "Fusarium wilt of banana" is about Panama
    even when its own sentences say only "the disease".

    ``declared`` is the set the source document covers. A single-disease document settles
    ambiguity on its own — a chunk in an FAO Fusarium manual is about Panama whatever else
    it happens to mention.
    """
    heading_text = " ".join(heading_path)
    scores = {
        disease: _score(text, terms) + 2 * _score(heading_text, terms)
        for disease, terms in _DISEASE_TERMS.items()
    }

    ranked = sorted(scores.items(), key=lambda pair: -pair[1])
    best, best_score = ranked[0]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        # No disease vocabulary at all. Fall back to the document's own scope.
        relevant = [d for d in declared if d in _DISEASE_TERMS]
        return relevant[0] if len(relevant) == 1 else GENERAL

    if best_score - runner_up_score < _MIN_MARGIN:
        # Two diseases discussed together. Trust the document if it only covers one.
        relevant = [d for d in declared if d in _DISEASE_TERMS]
        return relevant[0] if len(relevant) == 1 else GENERAL

    return best


def classify_topic(text: str, heading_path: list[str]) -> str:
    """Pick what the chunk is *about doing*, not just what it mentions."""
    heading_text = " ".join(heading_path)
    scores = {
        topic: _score(text, terms) + 3 * _score(heading_text, terms)
        for topic, terms in _TOPIC_TERMS.items()
    }

    best = max(scores.items(), key=lambda pair: pair[1])
    return best[0] if best[1] > 0 else GENERAL


def classify_chunks(
    chunks: list[Chunk], declared_by_slug: dict[str, tuple[str, ...]]
) -> ClassificationStats:
    """Assign disease and topic to every chunk, in place."""
    ambiguous = 0

    for chunk in chunks:
        declared = declared_by_slug.get(chunk.slug, ())
        chunk.disease = classify_disease(chunk.text, chunk.heading_path, declared)
        chunk.topic = classify_topic(chunk.text, chunk.heading_path)

        # Only count a miss when the document covers exactly one disease. Multi-topic
        # sources legitimately produce `general` chunks -- the Hawaii guidebook devotes
        # whole chapters to bunchy top virus and nematodes, which are neither of our
        # classes. Counting those as failures would report a broken classifier every run.
        single_disease = [d for d in declared if d in _DISEASE_TERMS]
        if chunk.disease == GENERAL and len(single_disease) == 1:
            ambiguous += 1

    return ClassificationStats(
        disease_counts=Counter(c.disease for c in chunks),
        topic_counts=Counter(c.topic for c in chunks),
        ambiguous_disease=ambiguous,
        n_chunks=len(chunks),
    )
