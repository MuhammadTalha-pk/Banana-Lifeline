"""Tests for metrics, calibration, and augmentation invariants.

These run without torch or a GPU wherever possible, so the invariants stay enforced in CI.
The ones that need torch skip cleanly when the training stack is absent.
"""

from __future__ import annotations

import numpy as np
import pytest

from banana_lifeline.config import AugmentationConfig, TrainConfig
from banana_lifeline.vision.calibrate import softmax
from banana_lifeline.vision.metrics import (
    aggregate_by_scene,
    compute_metrics,
    expected_calibration_error,
    risk_coverage_curve,
    threshold_for_target_risk,
)

sklearn = pytest.importorskip("sklearn", reason="metrics need scikit-learn")


# --------------------------------------------------------------------------------------
# The imbalance trap
# --------------------------------------------------------------------------------------


def test_accuracy_flatters_a_model_that_ignores_panama() -> None:
    """The reason macro-F1 is the reported metric and accuracy is not.

    A model predicting sigatoka for everything scores well on accuracy while being useless
    for the disease that kills the plant. Macro-F1 and panama recall expose it.
    """
    y_true = np.array([0] * 96 + [1] * 71 + [2] * 224)  # the real test distribution
    y_pred = np.full_like(y_true, 2)  # always "sigatoka"

    metrics = compute_metrics(y_true, y_pred)

    assert metrics.accuracy > 0.55
    assert metrics.macro_f1 < 0.30
    assert metrics.panama_recall == 0.0


def test_perfect_predictions_score_one() -> None:
    y_true = np.array([0, 1, 2, 0, 1, 2])
    metrics = compute_metrics(y_true, y_true)

    assert metrics.accuracy == 1.0
    assert metrics.macro_f1 == 1.0
    assert metrics.panama_recall == 1.0


def test_confusion_matrix_orientation() -> None:
    """Rows are truth, columns are prediction. Getting this backwards misreads every result."""
    y_true = np.array([1, 1, 1])
    y_pred = np.array([2, 2, 2])  # all panama predicted as sigatoka

    metrics = compute_metrics(y_true, y_pred)
    assert metrics.confusion[1][2] == 3
    assert metrics.confusion[2][1] == 0


# --------------------------------------------------------------------------------------
# Scene-level aggregation
# --------------------------------------------------------------------------------------


def test_scene_aggregation_collapses_duplicate_photos() -> None:
    """One plant photographed five times should count once, not five times.

    Scenes come back ordered by cluster id, so cluster 7 precedes cluster 9.
    """
    y_true = np.array([1, 1, 1, 1, 1, 0])
    y_pred = np.array([1, 1, 2, 1, 1, 0])
    clusters = np.array([7, 7, 7, 7, 7, 9])

    scene_true, scene_pred = aggregate_by_scene(y_true, y_pred, clusters)

    assert len(scene_true) == 2
    assert scene_true.tolist() == [1, 0]
    # Majority vote over cluster 7 rescues the single misclassified frame.
    assert scene_pred.tolist() == [1, 0]


def test_scene_metrics_are_reported_when_clusters_given() -> None:
    y_true = np.array([0, 0, 1, 1])
    metrics = compute_metrics(y_true, y_true, cluster_ids=np.array([1, 1, 2, 2]))

    assert metrics.scene_accuracy == 1.0
    assert metrics.scene_macro_f1 is not None


# --------------------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------------------


def test_softmax_normalises() -> None:
    probs = softmax(np.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]]))
    np.testing.assert_allclose(probs.sum(axis=1), 1.0)


def test_temperature_never_changes_a_prediction() -> None:
    """Temperature scaling adjusts confidence, not the decision.

    Dividing all logits by one positive scalar preserves the argmax. This is why calibration
    can be applied after training without re-validating accuracy.
    """
    rng = np.random.default_rng(0)
    logits = rng.normal(size=(200, 3)) * 3

    baseline = softmax(logits, 1.0).argmax(axis=1)
    for temperature in (0.5, 1.5, 2.0, 5.0):
        assert (softmax(logits, temperature).argmax(axis=1) == baseline).all()


def test_higher_temperature_lowers_confidence() -> None:
    logits = np.array([[5.0, 1.0, 0.0]])
    assert softmax(logits, 2.0).max() < softmax(logits, 1.0).max()


def test_ece_is_zero_for_a_perfectly_calibrated_model() -> None:
    confidences = np.full(1000, 0.8)
    rng = np.random.default_rng(0)
    correct = (rng.random(1000) < 0.8).astype(float)

    assert expected_calibration_error(confidences, correct) < 0.05


def test_ece_detects_overconfidence() -> None:
    """A model claiming 0.99 while right half the time should score badly."""
    confidences = np.full(1000, 0.99)
    correct = np.tile([1.0, 0.0], 500)

    assert expected_calibration_error(confidences, correct) > 0.4


# --------------------------------------------------------------------------------------
# Abstention
# --------------------------------------------------------------------------------------


def test_risk_falls_as_coverage_falls() -> None:
    """Answering only confident cases should reduce the error rate."""
    rng = np.random.default_rng(0)
    confidences = rng.uniform(0.34, 1.0, 500)
    correct = (rng.random(500) < confidences).astype(float)

    curve = risk_coverage_curve(confidences, correct)
    high_confidence = curve[len(curve) // 10]["risk"]
    everything = curve[-1]["risk"]

    assert high_confidence < everything


def test_threshold_selection_meets_the_target() -> None:
    rng = np.random.default_rng(1)
    confidences = rng.uniform(0.34, 1.0, 2000)
    correct = (rng.random(2000) < confidences).astype(float)

    threshold, coverage = threshold_for_target_risk(confidences, correct, target_risk=0.05)
    answered = confidences >= threshold

    assert 0 < coverage <= 1
    assert correct[answered].mean() >= 0.90


def test_impossible_target_yields_zero_coverage() -> None:
    """When no threshold meets the target, say so rather than returning a best effort."""
    confidences = np.full(100, 0.9)
    correct = np.zeros(100)  # always wrong

    threshold, coverage = threshold_for_target_risk(confidences, correct, target_risk=0.01)
    assert coverage == 0.0
    assert threshold == 1.0


# --------------------------------------------------------------------------------------
# Augmentation invariants
# --------------------------------------------------------------------------------------


def test_hue_jitter_is_disabled_by_default() -> None:
    """Leaf yellowing IS the label. Hue augmentation manufactures wrong training data."""
    assert AugmentationConfig().hue_shift == 0.0


def test_train_transform_rejects_hue_jitter() -> None:
    """The guard must actually fire, not just document an intention."""
    pytest.importorskip("albumentations")
    from banana_lifeline.vision.transforms import build_train_transform

    with pytest.raises(ValueError, match="leaf colour is the class signal"):
        build_train_transform(384, AugmentationConfig(hue_shift=0.1))


def test_default_resolution_preserves_lesion_detail() -> None:
    """384, not 224: Sigatoka's speckling does not survive the smaller size."""
    assert TrainConfig().image_size == 384


def test_default_amp_dtype_suits_a_t4() -> None:
    """T4 is Turing: fp16 tensor cores, no bf16. bfloat16 here would silently fall back."""
    assert TrainConfig().amp_dtype == "float16"


def test_monitor_metric_is_not_accuracy() -> None:
    assert TrainConfig().monitor_metric == "macro_f1"


def test_balanced_sampling_is_on_by_default() -> None:
    assert TrainConfig().balanced_sampling is True


def test_effective_batch_size_accounts_for_accumulation() -> None:
    cfg = TrainConfig(batch_size=16, grad_accum_steps=2)
    assert cfg.effective_batch_size == 32


# --------------------------------------------------------------------------------------
# Calibration must travel with the checkpoint
# --------------------------------------------------------------------------------------


def test_uncalibrated_checkpoint_is_detectable() -> None:
    """A freshly trained checkpoint carries temperature=1.0 and no threshold.

    Regression guard for a real defect: calibration was fitted after training and written
    only into the evaluation report, so the shipped checkpoint claimed temperature 1.0.
    Anything consuming that confidence would have been silently overconfident and the
    abstain threshold would never have fired.
    """
    from banana_lifeline.vision.model import LoadedModel

    fresh = LoadedModel(
        model=None,
        train_config=TrainConfig(),
        class_names=("healthy", "panama", "sigatoka"),
        temperature=1.0,
        metrics={},
        abstain_threshold=None,
    )
    assert fresh.is_calibrated is False

    calibrated = LoadedModel(
        model=None,
        train_config=TrainConfig(),
        class_names=("healthy", "panama", "sigatoka"),
        temperature=2.582,
        metrics={},
        abstain_threshold=0.936,
    )
    assert calibrated.is_calibrated is True


def test_temperature_without_threshold_is_not_calibrated() -> None:
    """Both halves are required: a temperature with no threshold cannot gate anything."""
    from banana_lifeline.vision.model import LoadedModel

    half = LoadedModel(
        model=None,
        train_config=TrainConfig(),
        class_names=("healthy", "panama", "sigatoka"),
        temperature=2.5,
        metrics={},
        abstain_threshold=None,
    )
    assert half.is_calibrated is False


def test_shipped_checkpoint_carries_its_calibration() -> None:
    """The model we would actually deploy must not ship uncalibrated."""
    from banana_lifeline.config import get_paths

    checkpoint = get_paths().runs / "cpu_clean" / "best.pt"
    if not checkpoint.is_file():
        pytest.skip("no trained checkpoint yet")

    torch = pytest.importorskip("torch")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)

    assert payload.get("temperature", 1.0) != 1.0, "checkpoint ships uncalibrated"
    assert payload.get("abstain_threshold") is not None, "checkpoint has no abstain threshold"
    assert 0.0 < payload["abstain_threshold"] <= 1.0
