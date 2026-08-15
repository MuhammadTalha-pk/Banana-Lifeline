"""Out-of-distribution rejection.

A three-class softmax always returns one of three diseases. Photograph a goat, a shoe, or
your thumb, and the model will confidently diagnose Sigatoka — it has no way to express
"that isn't a banana leaf". Farmers will absolutely photograph the wrong thing, so without
this the app is confidently wrong on a predictable fraction of real use.

Two tiers, cheapest first:

**Tier 1 — image quality.** Blur, exposure, and how much of the frame is vegetation. Pure
arithmetic on pixels, microseconds, no model. Catches the common cases (motion blur, a
finger over the lens, a photo of the sky) and returns advice a farmer can act on.

**Tier 2 — feature-space distance. IMPLEMENTED BUT DISABLED; it does not work here.**

The Mahalanobis approach is standard and it failed on this model, in a way worth recording
so nobody re-derives it:

* Fitted on training features, it rejected **100% of unseen real leaves**. Training images
  score 18-40; genuine held-out leaves score 56-130. It had learned "did the model memorise
  this exact image", not "is this a banana leaf".
* Fitted on validation features instead, the same inversion appeared against test data.
* The cause is dimensional: 1,280 features against ~1,800 samples makes the covariance
  estimate degenerate, so it separates whatever it was fitted on from everything else.
* Reducing to 16/32/64 dimensions with PCA did not rescue it. At every setting a flat grey
  rectangle scored as *more* normal than a real leaf -- the ordering is inverted, not merely
  weak.

Fixing it properly needs a real negative set (other crops, soil, hands, sky) to validate
against, and probably an energy or MSP baseline measured alongside. Until then only tier 1
runs. Shipping a detector that rejects every genuine photo would be far worse than shipping
none, and the numbers above are the evidence rather than an opinion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

#: Variance of the Laplacian below which an image is too blurry to diagnose. Calibrated
#: against the corpus: real farmer photos sit far above this, and lesion texture is exactly
#: what blur destroys first.
BLUR_THRESHOLD = 60.0

#: Mean brightness bounds. Outside these, detail is lost to shadow or blown highlights.
DARK_THRESHOLD = 40.0
BRIGHT_THRESHOLD = 225.0

#: Minimum fraction of the frame that must look like vegetation. A banana leaf photo is
#: overwhelmingly green/yellow/brown; a face, a wall, or the sky is not.
MIN_VEGETATION_FRACTION = 0.15


class Verdict(StrEnum):
    """What the gate decided, and therefore what the app should do next."""

    OK = "ok"
    TOO_BLURRY = "too_blurry"
    TOO_DARK = "too_dark"
    TOO_BRIGHT = "too_bright"
    NOT_VEGETATION = "not_vegetation"
    OUT_OF_DISTRIBUTION = "out_of_distribution"


#: What a farmer is told, phrased as an action rather than a diagnosis of their photography.
ADVICE: dict[Verdict, str] = {
    Verdict.OK: "",
    Verdict.TOO_BLURRY: "The photo is blurry. Hold the phone steady, tap the leaf on screen "
    "to focus, and take it again.",
    Verdict.TOO_DARK: "The photo is too dark. Move into daylight or turn on the flash.",
    Verdict.TOO_BRIGHT: "The photo is washed out by strong light. Stand so your shadow falls "
    "across the leaf, or move out of direct sun.",
    Verdict.NOT_VEGETATION: "I could not find a plant in this photo. Point the camera at a "
    "banana leaf so it fills most of the frame.",
    Verdict.OUT_OF_DISTRIBUTION: "This does not look like a banana leaf. If it is one, move "
    "closer so the leaf fills the frame.",
}


@dataclass(slots=True)
class QualityReport:
    """Tier-1 measurements, kept as numbers so a borderline reject can be explained."""

    verdict: Verdict
    blur_score: float
    brightness: float
    vegetation_fraction: float

    @property
    def passed(self) -> bool:
        return self.verdict is Verdict.OK

    @property
    def advice(self) -> str:
        return ADVICE[self.verdict]


def assess_quality(image: Any) -> QualityReport:
    """Tier 1: is this photo good enough to diagnose from at all?

    ``image`` is anything PIL can open, or a numpy array.
    """
    from PIL import Image

    if not isinstance(image, np.ndarray):
        if isinstance(image, str | Path):
            with Image.open(image) as handle:
                array = np.asarray(handle.convert("RGB"), dtype=np.float32)
        else:
            array = np.asarray(image.convert("RGB"), dtype=np.float32)
    else:
        array = image.astype(np.float32)

    grey = array.mean(axis=2)

    # Laplacian variance: sharp edges produce a wide response distribution, blur narrows it.
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    from numpy.lib.stride_tricks import sliding_window_view

    windows = sliding_window_view(grey, (3, 3))
    blur_score = float((windows * kernel).sum(axis=(2, 3)).var())

    brightness = float(grey.mean())

    # Vegetation: green dominant, or the yellow/brown of a diseased leaf. Deliberately not
    # "green only" -- a dying banana leaf is brown, and refusing to look at dead tissue
    # would reject exactly the photos that matter most.
    red, green, blue = array[:, :, 0], array[:, :, 1], array[:, :, 2]
    greenish = (green > blue * 1.05) & (green > 30)
    yellow_brown = (red > blue * 1.15) & (green > blue * 1.05) & (red > 40)
    vegetation_fraction = float((greenish | yellow_brown).mean())

    if blur_score < BLUR_THRESHOLD:
        verdict = Verdict.TOO_BLURRY
    elif brightness < DARK_THRESHOLD:
        verdict = Verdict.TOO_DARK
    elif brightness > BRIGHT_THRESHOLD:
        verdict = Verdict.TOO_BRIGHT
    elif vegetation_fraction < MIN_VEGETATION_FRACTION:
        verdict = Verdict.NOT_VEGETATION
    else:
        verdict = Verdict.OK

    return QualityReport(
        verdict=verdict,
        blur_score=blur_score,
        brightness=brightness,
        vegetation_fraction=vegetation_fraction,
    )


@dataclass(slots=True)
class MahalanobisDetector:
    """Distance to the nearest class centroid in the model's own feature space.

    Softmax confidence is a poor OOD signal because it only compares the three classes to
    each other -- an image unlike all of them still has to sum to 1, so one class wins by
    default. Distance asks a different question: does this look like *anything* the model
    was trained on?
    """

    means: np.ndarray  # (n_classes, n_features)
    precision: np.ndarray  # shared inverse covariance
    threshold: float = float("inf")

    def score(self, features: np.ndarray) -> np.ndarray:
        """Minimum Mahalanobis distance to any class. Higher means more out of distribution."""
        if features.ndim == 1:
            features = features[None, :]

        distances = np.empty((features.shape[0], self.means.shape[0]), dtype=np.float64)
        for index, mean in enumerate(self.means):
            centred = features - mean
            distances[:, index] = np.einsum("ij,jk,ik->i", centred, self.precision, centred)

        nearest: np.ndarray = np.sqrt(np.maximum(distances.min(axis=1), 0.0))
        return nearest

    def is_ood(self, features: np.ndarray) -> np.ndarray:
        return self.score(features) > self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "means": self.means.tolist(),
            "precision": self.precision.tolist(),
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MahalanobisDetector:
        return cls(
            means=np.asarray(payload["means"], dtype=np.float64),
            precision=np.asarray(payload["precision"], dtype=np.float64),
            threshold=float(payload.get("threshold", float("inf"))),
        )


def fit_mahalanobis(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    shrinkage: float = 1e-3,
) -> MahalanobisDetector:
    """Fit per-class means and a shared covariance over training features.

    A shared covariance rather than per-class: with 329 panama training images and 768
    feature dimensions, a per-class covariance is wildly underdetermined and would fit noise.
    Shrinkage keeps the inverse numerically stable.
    """
    n_features = features.shape[1]
    classes = np.unique(labels)

    means = np.stack([features[labels == c].mean(axis=0) for c in classes])

    centred = np.concatenate([features[labels == c] - means[i] for i, c in enumerate(classes)])
    covariance = np.cov(centred, rowvar=False) + shrinkage * np.eye(n_features)

    return MahalanobisDetector(means=means, precision=np.linalg.pinv(covariance))


def choose_threshold(
    in_distribution_scores: np.ndarray,
    *,
    target_tpr: float = 0.95,
) -> float:
    """Threshold accepting ``target_tpr`` of genuine banana leaves.

    Set from in-distribution data alone, because a representative set of "everything a
    farmer might photograph instead" does not exist and pretending otherwise would tune the
    threshold to whatever negatives happened to be collected.
    """
    return float(np.quantile(in_distribution_scores, target_tpr))


def evaluate_ood(
    in_scores: np.ndarray,
    out_scores: np.ndarray,
    threshold: float,
) -> dict[str, float]:
    """AUROC and FPR@95TPR, so the claim is measured rather than asserted."""
    from sklearn.metrics import roc_auc_score

    labels = np.concatenate([np.zeros(len(in_scores)), np.ones(len(out_scores))])
    scores = np.concatenate([in_scores, out_scores])

    accepted_in = float((in_scores <= threshold).mean())
    accepted_out = float((out_scores <= threshold).mean())

    return {
        "auroc": float(roc_auc_score(labels, scores)),
        "tpr_at_threshold": accepted_in,
        "fpr_at_threshold": accepted_out,
        "threshold": float(threshold),
    }
