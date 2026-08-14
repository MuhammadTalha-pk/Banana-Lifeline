"""Confidence calibration and the abstain threshold.

The product promise is that when the model is unsure, it says so and asks for a better photo
or an expert. That promise is empty unless the confidence number means something, and raw
neural-network softmax is systematically overconfident -- a network reporting 0.95 is
routinely right far less than 95% of the time.

Temperature scaling fixes this with a single scalar fitted on validation data. It cannot
change any prediction (dividing all logits by one positive number preserves the argmax), so
accuracy is untouched; it only makes the confidence honest. The abstain threshold is then
chosen from a risk-coverage curve against a target error rate, rather than picked as a
round number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from banana_lifeline.vision.metrics import (
    expected_calibration_error,
    risk_coverage_curve,
    threshold_for_target_risk,
)


@dataclass(slots=True)
class CalibrationResult:
    """Fitted temperature plus the evidence that it helped."""

    temperature: float
    ece_before: float
    ece_after: float
    threshold: float
    coverage_at_threshold: float
    target_risk: float
    curve: list[dict[str, float]]

    def summary(self) -> str:
        return (
            f"T={self.temperature:.3f}  ECE {self.ece_before:.4f} -> {self.ece_after:.4f}  "
            f"abstain below {self.threshold:.3f} "
            f"(answers {self.coverage_at_threshold * 100:.0f}% at <={self.target_risk:.0%} risk)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "ece_before": self.ece_before,
            "ece_after": self.ece_after,
            "threshold": self.threshold,
            "coverage_at_threshold": self.coverage_at_threshold,
            "target_risk": self.target_risk,
        }


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    scaled = logits / temperature
    shifted = scaled - scaled.max(axis=1, keepdims=True)  # numerical stability
    exponentiated = np.exp(shifted)
    normalised: np.ndarray = exponentiated / exponentiated.sum(axis=1, keepdims=True)
    return normalised


def fit_temperature(
    logits: np.ndarray,
    labels: np.ndarray,
    *,
    max_iter: int = 200,
) -> float:
    """Fit the scalar temperature that minimises validation NLL.

    Optimised in log-space so temperature stays positive; a negative or zero temperature
    would invert or destroy the probability ordering.
    """
    import torch

    logit_tensor = torch.as_tensor(logits, dtype=torch.float32)
    label_tensor = torch.as_tensor(labels, dtype=torch.long)
    log_temperature = torch.zeros(1, requires_grad=True)  # T = exp(0) = 1

    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=max_iter)
    criterion = torch.nn.CrossEntropyLoss()

    def closure() -> Any:
        optimizer.zero_grad()
        loss = criterion(logit_tensor / log_temperature.exp(), label_tensor)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_temperature.exp().item())


def calibrate(
    logits: np.ndarray,
    labels: np.ndarray,
    *,
    target_risk: float = 0.05,
) -> CalibrationResult:
    """Fit temperature and choose an abstain threshold for a target error rate.

    ``target_risk=0.05`` means: among the cases the model chooses to answer, at most 5%
    should be wrong. Everything below the resulting threshold is routed to "ask for a clearer
    photo or consult an expert" rather than being answered.
    """
    temperature = fit_temperature(logits, labels)

    probs_before = softmax(logits, 1.0)
    probs_after = softmax(logits, temperature)
    correct = (probs_after.argmax(axis=1) == labels).astype(float)

    threshold, coverage = threshold_for_target_risk(
        probs_after.max(axis=1), correct, target_risk=target_risk
    )

    return CalibrationResult(
        temperature=temperature,
        ece_before=expected_calibration_error(probs_before.max(axis=1), correct),
        ece_after=expected_calibration_error(probs_after.max(axis=1), correct),
        threshold=threshold,
        coverage_at_threshold=coverage,
        target_risk=target_risk,
        curve=risk_coverage_curve(probs_after.max(axis=1), correct),
    )
