"""Tests for the decision policy and the generation safety rules.

Every case here is a way a farmer could be harmed by a fluent, confident, wrong answer.
These are the highest-stakes tests in the project: a bug in retrieval costs relevance, a bug
here costs someone their crop.
"""

from __future__ import annotations

import numpy as np
import pytest

from banana_lifeline.generation import safety
from banana_lifeline.generation.answer import answer_follow_up
from banana_lifeline.vision.ood import (
    BLUR_THRESHOLD,
    QualityReport,
    Verdict,
    assess_quality,
    fit_mahalanobis,
)
from banana_lifeline.vision.policy import Action, decide

# --------------------------------------------------------------------------------------
# Image quality gate
# --------------------------------------------------------------------------------------


def _leaf_like(size: int = 128, *, sharp: bool = True, brightness: float = 120.0) -> np.ndarray:
    """A synthetic image with vegetation colours and optional texture."""
    rng = np.random.default_rng(0)
    image = np.zeros((size, size, 3), dtype=np.float32)
    image[:, :, 1] = brightness * 1.2  # green dominant
    image[:, :, 0] = brightness * 0.9
    image[:, :, 2] = brightness * 0.5
    if sharp:
        image += rng.normal(0, 40, image.shape).astype(np.float32)
    return np.clip(image, 0, 255)


def test_a_good_leaf_photo_passes() -> None:
    report = assess_quality(_leaf_like())
    assert report.passed
    assert report.advice == ""


def test_blurry_photos_are_rejected_with_actionable_advice() -> None:
    """The message must tell a farmer what to DO, not grade their photography."""
    report = assess_quality(_leaf_like(sharp=False))

    assert report.verdict is Verdict.TOO_BLURRY
    assert report.blur_score < BLUR_THRESHOLD
    assert "steady" in report.advice.lower()


def test_dark_photos_are_rejected() -> None:
    report = assess_quality(_leaf_like(brightness=15.0))
    assert report.verdict in {Verdict.TOO_DARK, Verdict.TOO_BLURRY}


def test_non_vegetation_is_rejected() -> None:
    """A blue sky or a grey wall is not a leaf, however sharp the photo."""
    rng = np.random.default_rng(1)
    sky = np.zeros((128, 128, 3), dtype=np.float32)
    sky[:, :, 2] = 200  # blue dominant
    sky[:, :, 0] = 90
    sky[:, :, 1] = 120
    sky += rng.normal(0, 40, sky.shape).astype(np.float32)

    assert assess_quality(np.clip(sky, 0, 255)).verdict is Verdict.NOT_VEGETATION


def test_brown_dead_leaves_still_count_as_vegetation() -> None:
    """Refusing dead tissue would reject exactly the photos that matter most."""
    rng = np.random.default_rng(2)
    dead = np.zeros((128, 128, 3), dtype=np.float32)
    dead[:, :, 0] = 150  # brown: red > green > blue
    dead[:, :, 1] = 110
    dead[:, :, 2] = 60
    dead += rng.normal(0, 40, dead.shape).astype(np.float32)

    assert assess_quality(np.clip(dead, 0, 255)).verdict is not Verdict.NOT_VEGETATION


# --------------------------------------------------------------------------------------
# Mahalanobis OOD
# --------------------------------------------------------------------------------------


def test_ood_detector_separates_far_from_near() -> None:
    rng = np.random.default_rng(0)
    features = np.concatenate(
        [
            rng.normal(0, 1, (60, 8)),
            rng.normal(5, 1, (60, 8)),
        ]
    )
    labels = np.array([0] * 60 + [1] * 60)

    detector = fit_mahalanobis(features, labels)
    near = detector.score(rng.normal(0, 1, (10, 8)))
    far = detector.score(rng.normal(40, 1, (10, 8)))

    assert far.mean() > near.mean() * 3


def test_ood_detector_round_trips_through_a_dict() -> None:
    from banana_lifeline.vision.ood import MahalanobisDetector

    rng = np.random.default_rng(0)
    original = fit_mahalanobis(rng.normal(0, 1, (40, 5)), np.array([0] * 20 + [1] * 20))
    original.threshold = 3.5

    restored = MahalanobisDetector.from_dict(original.to_dict())
    probe = rng.normal(0, 1, (5, 5))
    np.testing.assert_allclose(original.score(probe), restored.score(probe))


# --------------------------------------------------------------------------------------
# The decision policy
# --------------------------------------------------------------------------------------


def _ok_quality() -> QualityReport:
    return QualityReport(Verdict.OK, blur_score=500.0, brightness=120.0, vegetation_fraction=0.8)


def _bad_quality() -> QualityReport:
    return QualityReport(
        Verdict.TOO_BLURRY, blur_score=10.0, brightness=120.0, vegetation_fraction=0.8
    )


def test_a_bad_photo_never_reaches_the_classifier() -> None:
    decision = decide(quality=_bad_quality(), disease="sigatoka", confidence=0.99)

    assert decision.action is Action.RETAKE_PHOTO
    assert decision.disease is None
    assert not decision.should_retrieve


def test_out_of_distribution_beats_high_confidence() -> None:
    """A confident softmax on a photo of a goat is still a photo of a goat."""
    decision = decide(quality=_ok_quality(), disease="sigatoka", confidence=0.99, is_ood=True)

    assert decision.action is Action.RETAKE_PHOTO
    assert decision.disease is None


def test_panama_never_gets_asserted_from_a_leaf_photo() -> None:
    """Even at maximum confidence.

    Panama is diagnosed from whole-plant collapse and brown vascular tissue inside a cut
    stem. An expert ruled 16 of 18 contested images in this dataset undecidable from the
    leaf alone, so the model asserting it would be claiming more than the evidence allows.
    """
    decision = decide(quality=_ok_quality(), disease="panama", confidence=0.999)

    assert decision.action is Action.ASK_FOLLOW_UP
    assert len(decision.follow_up_questions) >= 3
    assert any("brown" in q.lower() for q in decision.follow_up_questions)


def test_low_confidence_refuses_to_name_a_disease() -> None:
    """Naming a disease here is how a farmer treats the wrong thing."""
    decision = decide(quality=_ok_quality(), disease="sigatoka", confidence=0.40)

    assert decision.action is Action.REFER_TO_EXPERT
    assert decision.disease is None
    assert "extension officer" in decision.message


def test_middling_confidence_answers_with_a_caveat() -> None:
    decision = decide(quality=_ok_quality(), disease="sigatoka", confidence=0.75)

    assert decision.action is Action.ANSWER_WITH_CAVEAT
    assert decision.disease == "sigatoka"
    assert "not certain" in decision.message


def test_high_confidence_answers_plainly() -> None:
    decision = decide(quality=_ok_quality(), disease="sigatoka", confidence=0.98)

    assert decision.action is Action.ANSWER
    assert decision.should_retrieve


def test_every_decision_records_why() -> None:
    """An answer a farmer acts on must be explainable after the fact."""
    for confidence in (0.2, 0.6, 0.99):
        assert decide(quality=_ok_quality(), disease="healthy", confidence=confidence).reason


# --------------------------------------------------------------------------------------
# Safety rules
# --------------------------------------------------------------------------------------


def test_a_fungicide_cure_for_panama_is_blocked() -> None:
    """The single most dangerous plausible output.

    Models have read thousands of "banana disease -> apply fungicide" documents, so a spray
    schedule is the fluent completion. It is wrong: Fusarium is soil-borne and vascular, so
    the farmer loses the money AND the crop while the disease spreads.
    """
    text = "Spray propiconazole every 14 days to cure Panama disease completely."
    result = safety.enforce(text, disease="panama", source_texts=[], source_regions=["global"])

    assert result.blocked
    assert "no chemical cure" in result.amended_text.lower()
    assert "propiconazole" not in result.amended_text


def test_panama_containment_advice_is_allowed() -> None:
    text = (
        "There is no chemical cure for Panama disease. Destroy affected plants and "
        "disinfect tools between plants."
    )
    result = safety.enforce(
        text, disease="panama", source_texts=[text], source_regions=["pakistan"]
    )
    assert not result.blocked


def test_an_invented_dosage_is_blocked() -> None:
    """A quantity may be quoted from a source. It may never be recalled or calculated."""
    sources = [
        "Apply mancozeb as a protectant spray. Wear gloves. Observe the pre-harvest interval."
    ]
    text = "Apply mancozeb at 2.5 kg/ha every 14 days. Wear gloves. Check the pre-harvest interval."

    result = safety.enforce(
        text, disease="sigatoka", source_texts=sources, source_regions=["pakistan"]
    )

    assert result.blocked
    assert any(v.rule == "ungrounded_dosage" for v in result.violations)


def test_a_dosage_quoted_from_a_source_survives() -> None:
    sources = [
        "Apply mancozeb at 2.5 kg/ha. Wear protective clothing. Pre-harvest interval 21 days."
    ]
    text = "Apply mancozeb at 2.5 kg/ha. Wear protective clothing. Pre-harvest interval is 21 days."

    result = safety.enforce(
        text, disease="sigatoka", source_texts=sources, source_regions=["pakistan"]
    )
    assert not result.blocked


def test_chemical_advice_gains_ppe_and_interval_warnings() -> None:
    sources = ["Spray a protectant fungicide when lesions appear."]
    text = "Spray a protectant fungicide when lesions appear."

    result = safety.enforce(
        text, disease="sigatoka", source_texts=sources, source_regions=["pakistan"]
    )

    rules = {v.rule for v in result.violations}
    assert "missing_ppe" in rules
    assert "missing_preharvest_interval" in rules
    assert "gloves" in result.amended_text.lower()


def test_tr4_triggers_official_reporting_guidance() -> None:
    """TR4 is a quarantine pathogen. Treating it as a private problem spreads it."""
    text = "TR4 has been found in several countries and affects Cavendish bananas."
    result = safety.enforce(text, disease="panama", source_texts=[text], source_regions=["global"])

    assert any(v.rule == "tr4_not_escalated" for v in result.violations)
    assert "report" in result.amended_text.lower()


def test_foreign_chemical_advice_gains_a_registration_caveat() -> None:
    """Pesticide registration is jurisdiction-specific and no source here is Pakistani."""
    sources = ["Spray carbendazim. Wear gloves. Pre-harvest interval applies."]
    text = "Spray carbendazim. Wear gloves. Observe the pre-harvest interval."

    result = safety.enforce(
        text, disease="sigatoka", source_texts=sources, source_regions=["india", "global"]
    )

    assert any(v.rule == "foreign_region_advice" for v in result.violations)
    assert "pakistan" in result.amended_text.lower()


def test_clean_non_chemical_advice_passes_untouched() -> None:
    text = "Remove and destroy infected leaves. Improve drainage around the plants."
    result = safety.enforce(
        text, disease="sigatoka", source_texts=[text], source_regions=["pakistan"]
    )

    assert result.is_clean
    assert result.amended_text == text


# --------------------------------------------------------------------------------------
# Panama follow-up scoring
# --------------------------------------------------------------------------------------


def test_vascular_browning_dominates_the_follow_up_score() -> None:
    """Brown lines inside a cut stem are near-definitive; leaf yellowing alone is not.

    Yellowing older leaves is shared with potassium deficiency and drought.
    """
    _, stem_only = answer_follow_up({"brown_lines_inside_stem": True})
    _, leaves_only = answer_follow_up({"older_leaves_yellow_first": True})

    assert stem_only > leaves_only


def test_strong_evidence_recommends_containment_not_treatment() -> None:
    message, score = answer_follow_up(
        {
            "older_leaves_yellow_first": True,
            "leaves_collapse_around_stem": True,
            "brown_lines_inside_stem": True,
        }
    )

    assert score >= 0.60
    assert "no chemical cure" in message.lower()
    assert "report" in message.lower()


def test_weak_evidence_suggests_another_cause() -> None:
    message, score = answer_follow_up({"older_leaves_yellow_first": False})

    assert score < 0.30
    assert "nutrient" in message.lower() or "waterlog" in message.lower()


@pytest.mark.parametrize("responses", [{}, {"unknown_key": True}])
def test_follow_up_handles_missing_answers(responses: dict[str, bool]) -> None:
    message, score = answer_follow_up(responses)
    assert score == 0.0
    assert message
