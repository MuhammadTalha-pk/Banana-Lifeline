"""The decision policy.

Every path between a photograph and what a farmer is told converges here. It is deliberately
one small, pure, fully-tested function rather than conditionals scattered through the app:
this is the logic standing between someone's crop and a wrong answer, and it should be
readable in one sitting.

The ordering encodes a principle — **cheapest and most certain rejections first**. There is
no point running a Mahalanobis distance on a photo that is too blurry to diagnose, and no
point discussing confidence for a picture of a goat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from banana_lifeline.config import CLASS_NAMES
from banana_lifeline.vision.ood import ADVICE, QualityReport, Verdict


class Action(StrEnum):
    """What the app does next."""

    ANSWER = "answer"
    """Confident enough to state the disease and give guidance."""

    ANSWER_WITH_CAVEAT = "answer_with_caveat"
    """Show the likely disease, but say plainly that it is not certain."""

    ASK_FOLLOW_UP = "ask_follow_up"
    """Panama specifically: ask what a farmer can check before asserting."""

    RETAKE_PHOTO = "retake_photo"
    """The image itself is the problem; nothing can be diagnosed from it."""

    REFER_TO_EXPERT = "refer_to_expert"
    """A real banana leaf, but the model cannot call it. Send them to a human."""


#: Confidence floor for stating a diagnosis outright. From the calibrated risk-coverage
#: curve on the clean split, targeting <=5% error among answered cases.
CONFIDENT_THRESHOLD = 0.936

#: Below this, the model is guessing and should not name a disease at all.
CAVEAT_FLOOR = 0.55


@dataclass(slots=True)
class Decision:
    """What to do, why, and what to say."""

    action: Action
    disease: str | None
    confidence: float
    message: str
    reason: str
    follow_up_questions: list[str] = field(default_factory=list)

    @property
    def should_retrieve(self) -> bool:
        """Whether to fetch guidance. False for retakes -- there is no disease to look up."""
        return self.action in {
            Action.ANSWER,
            Action.ANSWER_WITH_CAVEAT,
            Action.ASK_FOLLOW_UP,
        }


#: Panama cannot be confirmed from a leaf photo. Its diagnostic signs are whole-plant
#: collapse and brown vascular tissue inside a cut pseudostem -- which is why an expert
#: reviewer ruled 16 of 18 contested images in this dataset undecidable from the leaf alone.
#: Rather than assert, the app asks what a farmer can actually go and look at.
PANAMA_FOLLOW_UP: tuple[str, ...] = (
    "Are the older, lower leaves turning yellow first, while the young top leaves stay green?",
    "Are the yellow leaves collapsing and hanging down around the stem, like a skirt?",
    "Cut across the trunk near the base — do you see brown or reddish lines inside?",
    "Is the base of the trunk splitting?",
)


def decide(
    *,
    quality: QualityReport,
    disease: str | None,
    confidence: float,
    is_ood: bool = False,
) -> Decision:
    """Decide what to tell the farmer.

    Pure and side-effect free so every branch is unit-testable, which matters more here than
    anywhere else in the system.
    """
    # 1. The photo itself, before anything is inferred from it.
    if not quality.passed:
        return Decision(
            action=Action.RETAKE_PHOTO,
            disease=None,
            confidence=0.0,
            message=quality.advice,
            reason=f"quality gate: {quality.verdict.value}",
        )

    # 2. A usable photo of the wrong thing.
    if is_ood:
        return Decision(
            action=Action.RETAKE_PHOTO,
            disease=None,
            confidence=0.0,
            message=ADVICE[Verdict.OUT_OF_DISTRIBUTION],
            reason="feature-space distance: unlike any training class",
        )

    if disease is None or disease not in CLASS_NAMES:
        return Decision(
            action=Action.REFER_TO_EXPERT,
            disease=None,
            confidence=confidence,
            message="I could not identify this. Please show it to a local agricultural "
            "extension officer.",
            reason="no valid class predicted",
        )

    # 3. Too uncertain to name a disease at all. Naming one here is how a farmer ends up
    #    treating the wrong thing.
    if confidence < CAVEAT_FLOOR:
        return Decision(
            action=Action.REFER_TO_EXPERT,
            disease=None,
            confidence=confidence,
            message="I am not confident enough to say what this is. Take another photo in "
            "good light, or ask a local agricultural extension officer.",
            reason=f"confidence {confidence:.2f} below floor {CAVEAT_FLOOR}",
        )

    # 4. Panama never gets asserted from a leaf alone, however confident the model is.
    if disease == "panama":
        return Decision(
            action=Action.ASK_FOLLOW_UP,
            disease="panama",
            confidence=confidence,
            message="This may be Panama disease (Fusarium wilt). A leaf photo alone cannot "
            "confirm it, so please check a few things on the plant.",
            reason="panama requires whole-plant confirmation",
            follow_up_questions=list(PANAMA_FOLLOW_UP),
        )

    if confidence >= CONFIDENT_THRESHOLD:
        return Decision(
            action=Action.ANSWER,
            disease=disease,
            confidence=confidence,
            message="",
            reason=f"confidence {confidence:.2f} at or above {CONFIDENT_THRESHOLD}",
        )

    return Decision(
        action=Action.ANSWER_WITH_CAVEAT,
        disease=disease,
        confidence=confidence,
        message="This looks like it may be "
        f"{disease}, but I am not certain. Compare it with the pictures below, and "
        "confirm with an extension officer before spending money on treatment.",
        reason=f"confidence {confidence:.2f} below {CONFIDENT_THRESHOLD}",
    )
