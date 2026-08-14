"""Metrics, chosen for an imbalanced three-class problem with asymmetric costs.

Accuracy is deliberately computed but never treated as the headline. Sigatoka outnumbers
panama roughly 4:1 in this corpus, so a model that never predicts panama at all still scores
around 80% accuracy while being useless for the disease that kills the plant. Macro-F1 and
per-class recall are what get reported and what early stopping monitors.

Scene-level metrics exist alongside image-level ones because the corpus contains multiple
photos of the same plant: a per-image average silently weights heavily-photographed plants
more, and a per-scene average is the closer analogue of "how often is a farmer served well".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from banana_lifeline.config import CLASS_NAMES


@dataclass(slots=True)
class ClassificationMetrics:
    """Everything measured on one evaluation pass."""

    accuracy: float
    macro_f1: float
    balanced_accuracy: float
    per_class_precision: dict[str, float]
    per_class_recall: dict[str, float]
    per_class_f1: dict[str, float]
    support: dict[str, int]
    confusion: list[list[int]]
    scene_accuracy: float | None = None
    scene_macro_f1: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def panama_recall(self) -> float:
        """Called out separately: missing panama is the most expensive error available."""
        return self.per_class_recall.get("panama", 0.0)

    def headline(self) -> str:
        return (
            f"macro-F1 {self.macro_f1:.3f} | balanced-acc {self.balanced_accuracy:.3f} | "
            f"panama recall {self.panama_recall:.3f} | accuracy {self.accuracy:.3f}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "macro_f1": self.macro_f1,
            "balanced_accuracy": self.balanced_accuracy,
            "panama_recall": self.panama_recall,
            "per_class_precision": self.per_class_precision,
            "per_class_recall": self.per_class_recall,
            "per_class_f1": self.per_class_f1,
            "support": self.support,
            "confusion": self.confusion,
            "scene_accuracy": self.scene_accuracy,
            "scene_macro_f1": self.scene_macro_f1,
            **self.extra,
        }


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    cluster_ids: np.ndarray | None = None,
    class_names: tuple[str, ...] = CLASS_NAMES,
) -> ClassificationMetrics:
    """Compute image-level metrics, and scene-level ones when cluster ids are supplied."""
    from sklearn.metrics import (
        balanced_accuracy_score,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
    )

    labels = list(range(len(class_names)))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )

    metrics = ClassificationMetrics(
        accuracy=float((y_true == y_pred).mean()),
        macro_f1=float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, y_pred)),
        per_class_precision={n: float(p) for n, p in zip(class_names, precision, strict=True)},
        per_class_recall={n: float(r) for n, r in zip(class_names, recall, strict=True)},
        per_class_f1={n: float(v) for n, v in zip(class_names, f1, strict=True)},
        support={n: int(s) for n, s in zip(class_names, support, strict=True)},
        confusion=confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    )

    if cluster_ids is not None:
        scene_true, scene_pred = aggregate_by_scene(y_true, y_pred, cluster_ids)
        metrics.scene_accuracy = float((scene_true == scene_pred).mean())
        metrics.scene_macro_f1 = float(
            f1_score(scene_true, scene_pred, labels=labels, average="macro", zero_division=0)
        )

    return metrics


def aggregate_by_scene(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cluster_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Collapse per-image predictions to one prediction per scene by majority vote."""
    scene_true: list[int] = []
    scene_pred: list[int] = []

    for cluster in np.unique(cluster_ids):
        mask = cluster_ids == cluster
        scene_true.append(int(np.bincount(y_true[mask]).argmax()))
        scene_pred.append(int(np.bincount(y_pred[mask]).argmax()))

    return np.array(scene_true), np.array(scene_pred)


def expected_calibration_error(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_bins: int = 15,
) -> float:
    """Gap between stated confidence and observed accuracy, averaged over bins.

    This is the number that decides whether a confidence threshold means anything. A model
    at 0.95 confidence should be right 95% of the time; an uncalibrated network is routinely
    right far less often, which would make an abstain threshold meaningless.
    """
    from itertools import pairwise

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    error = 0.0

    for low, high in pairwise(bins):
        mask = (confidences > low) & (confidences <= high)
        if not mask.any():
            continue
        weight = mask.mean()
        error += weight * abs(correct[mask].mean() - confidences[mask].mean())

    return float(error)


def risk_coverage_curve(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_points: int = 50,
) -> list[dict[str, float]]:
    """Trace error rate against the fraction of cases the model chooses to answer.

    This is how the abstain threshold gets chosen honestly: pick the coverage the product can
    live with, read off the error rate, and set the threshold there -- rather than guessing
    at a round number like 0.7 and hoping.
    """
    order = np.argsort(-confidences)
    sorted_correct = correct[order]
    sorted_conf = confidences[order]

    curve: list[dict[str, float]] = []
    for i in np.linspace(1, len(sorted_correct), n_points, dtype=int):
        answered = sorted_correct[:i]
        curve.append(
            {
                "coverage": float(i / len(sorted_correct)),
                "risk": float(1.0 - answered.mean()),
                "threshold": float(sorted_conf[i - 1]),
            }
        )
    return curve


def threshold_for_target_risk(
    confidences: np.ndarray,
    correct: np.ndarray,
    target_risk: float = 0.05,
) -> tuple[float, float]:
    """Lowest threshold whose answered set stays under ``target_risk``.

    Returns ``(threshold, coverage)``. Falling back to threshold 1.0 with zero coverage is
    the honest outcome when no threshold achieves the target: it says the model cannot meet
    that error bar at any operating point, which is information worth surfacing rather than
    hiding behind a best-effort number.
    """
    curve = risk_coverage_curve(confidences, correct, n_points=200)
    feasible = [point for point in curve if point["risk"] <= target_risk]
    if not feasible:
        return 1.0, 0.0

    best = max(feasible, key=lambda p: p["coverage"])
    return best["threshold"], best["coverage"]
