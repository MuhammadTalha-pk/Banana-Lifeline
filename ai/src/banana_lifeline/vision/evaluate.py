"""Test-set evaluation, the two-split comparison, and shortcut diagnostics.

Three things happen here that ordinary evaluation scripts skip:

* **The background ablation.** Every photo in this corpus was taken at one site on one day,
  so sky, soil, and lighting are nearly constant within a class. A model can reach high
  accuracy by reading context instead of pathology. Re-evaluating on an aggressive centre
  crop measures how much of the score survives when context is removed.
* **Scene-level metrics**, so heavily-photographed plants do not dominate the average.
* **The contaminated-versus-clean comparison table**, which is the point of preserving the
  original split at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from banana_lifeline.config import CLASS_NAMES, DataConfig, Paths, TrainConfig
from banana_lifeline.vision.metrics import ClassificationMetrics, compute_metrics


@dataclass(slots=True)
class EvaluationOutput:
    """Everything one evaluation pass produced."""

    metrics: ClassificationMetrics
    logits: np.ndarray
    labels: np.ndarray
    cluster_ids: np.ndarray
    relpaths: list[str]

    @property
    def probabilities(self) -> np.ndarray:
        from banana_lifeline.vision.calibrate import softmax

        return softmax(self.logits)


def predict(
    model: Any,
    manifest: pd.DataFrame,
    train_cfg: TrainConfig,
    data_cfg: DataConfig,
    paths: Paths,
    *,
    transform: Any | None = None,
    device: str | None = None,
) -> EvaluationOutput:
    """Run the model over a manifest split and collect raw logits."""
    import torch
    from torch.utils.data import DataLoader

    from banana_lifeline.data.dataset import BananaLeafDataset
    from banana_lifeline.vision.transforms import build_eval_transform

    resolved_device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model = model.to(resolved_device).eval()

    dataset = BananaLeafDataset(
        manifest.reset_index(drop=True),
        paths,
        data_cfg,
        transform=transform or build_eval_transform(train_cfg.image_size),
    )
    loader = DataLoader(
        dataset,
        batch_size=train_cfg.batch_size,
        shuffle=False,
        num_workers=train_cfg.num_workers,
        pin_memory=True,
    )

    logits: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    clusters: list[np.ndarray] = []
    relpaths: list[str] = []

    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(resolved_device, non_blocking=True)
            logits.append(model(images).float().cpu().numpy())
            labels.append(batch["label"].numpy())
            clusters.append(batch["cluster_id"].numpy())
            relpaths.extend(batch["relpath"])

    logits_array = np.concatenate(logits)
    labels_array = np.concatenate(labels)
    clusters_array = np.concatenate(clusters)

    return EvaluationOutput(
        metrics=compute_metrics(
            labels_array, logits_array.argmax(axis=1), cluster_ids=clusters_array
        ),
        logits=logits_array,
        labels=labels_array,
        cluster_ids=clusters_array,
        relpaths=relpaths,
    )


def background_ablation(
    model: Any,
    manifest: pd.DataFrame,
    train_cfg: TrainConfig,
    data_cfg: DataConfig,
    paths: Paths,
) -> ClassificationMetrics:
    """Re-evaluate on a tight centre crop to test for background shortcut learning.

    Interpretation: a small drop means the model reads the leaf, which is what we want. A
    large drop means much of the headline score came from context that will not generalise
    to a different farm, a different season, or a different sky.
    """
    from banana_lifeline.vision.transforms import build_background_ablation_transform

    return predict(
        model,
        manifest,
        train_cfg,
        data_cfg,
        paths,
        transform=build_background_ablation_transform(train_cfg.image_size),
    ).metrics


def confusion_table(metrics: ClassificationMetrics) -> str:
    """Render the confusion matrix as markdown, rows = truth, columns = prediction."""
    header = "| truth \\ pred | " + " | ".join(CLASS_NAMES) + " | recall |"
    divider = "|---" * (len(CLASS_NAMES) + 2) + "|"
    rows = [header, divider]

    for i, name in enumerate(CLASS_NAMES):
        counts = metrics.confusion[i]
        recall = metrics.per_class_recall[name]
        rows.append(f"| **{name}** | " + " | ".join(str(c) for c in counts) + f" | {recall:.3f} |")

    return "\n".join(rows)


def comparison_report(
    clean: ClassificationMetrics,
    original: ClassificationMetrics,
    *,
    ablation: ClassificationMetrics | None = None,
    calibration: dict[str, Any] | None = None,
) -> str:
    """The headline deliverable: what the contaminated split claims versus what is true."""
    gap = original.accuracy - clean.accuracy

    lines = [
        "# Model Evaluation — Banana Leaf Classifier",
        "",
        "## Contaminated split vs honest split",
        "",
        "Identical recipe, identical hyperparameters, identical quarantine. The only",
        "difference is how images were assigned to train/val/test.",
        "",
        "| Split | Accuracy | Macro-F1 | Balanced acc. | Panama recall |",
        "|---|---|---|---|---|",
        f"| Original (contaminated) | {original.accuracy:.3f} | {original.macro_f1:.3f} "
        f"| {original.balanced_accuracy:.3f} | {original.panama_recall:.3f} |",
        f"| **Clean (group-aware)** | **{clean.accuracy:.3f}** | **{clean.macro_f1:.3f}** "
        f"| **{clean.balanced_accuracy:.3f}** | **{clean.panama_recall:.3f}** |",
        "",
        f"The contaminated split overstates accuracy by **{gap:.1%}**. That gap is the",
        "portion of the original number that was memorisation: 60% of its held-out images",
        "had a near-identical twin in training.",
        "",
        "**The clean figures are the real ones.** They are what should appear in the report,",
        "the presentation, and any claim made about field performance.",
        "",
        "## Per-class performance (clean split)",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
    ]

    for name in CLASS_NAMES:
        lines.append(
            f"| {name} | {clean.per_class_precision[name]:.3f} "
            f"| {clean.per_class_recall[name]:.3f} | {clean.per_class_f1[name]:.3f} "
            f"| {clean.support[name]} |"
        )

    lines += [
        "",
        "Panama recall is the number to watch. Fusarium wilt kills the plant and has no",
        "chemical cure, so a missed panama case is the most expensive error the system can",
        "make -- and panama is the smallest class, with the fewest distinct scenes.",
        "",
        "## Confusion matrix (clean split)",
        "",
        confusion_table(clean),
        "",
    ]

    if clean.scene_macro_f1 is not None:
        lines += [
            "## Scene-level performance",
            "",
            f"Per-image macro-F1 {clean.macro_f1:.3f} against per-scene "
            f"{clean.scene_macro_f1:.3f}. Scene-level treats each photographed plant once,",
            "rather than letting a heavily-photographed plant count many times.",
            "",
        ]

    if ablation is not None:
        drop = clean.macro_f1 - ablation.macro_f1
        verdict = (
            "The model is largely reading the leaf."
            if drop < 0.10
            else "**A large share of performance came from background context, not pathology.** "
            "This will not transfer to a different farm or season."
        )
        lines += [
            "## Background ablation",
            "",
            "Every photo comes from one site on one day, so background and lighting barely",
            "vary between classes and a shortcut is readily available. Re-evaluating on a",
            "tight centre crop removes most context:",
            "",
            "| Full frame | Centre crop only | Drop |",
            "|---|---|---|",
            f"| {clean.macro_f1:.3f} | {ablation.macro_f1:.3f} | {drop:.3f} |",
            "",
            verdict,
            "",
        ]

    if calibration is not None:
        lines += [
            "## Calibration and abstention",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Temperature | {calibration['temperature']:.3f} |",
            f"| ECE before | {calibration['ece_before']:.4f} |",
            f"| ECE after | {calibration['ece_after']:.4f} |",
            f"| Abstain threshold | {calibration['threshold']:.3f} |",
            f"| Coverage at threshold | {calibration['coverage_at_threshold']:.1%} |",
            f"| Target risk | {calibration['target_risk']:.0%} |",
            "",
            "Temperature scaling cannot change a prediction -- it divides all logits by one",
            "positive scalar, so the argmax is untouched. It only makes the confidence",
            "number mean what it says, which is what allows a threshold to be trusted.",
            "",
            f"Below {calibration['threshold']:.3f} confidence the system does not answer; it",
            "asks for a clearer photo or refers the farmer to an extension officer.",
            "",
        ]

    return "\n".join(lines)


def write_evaluation(
    report: str,
    metrics: dict[str, Any],
    paths: Paths,
    *,
    name: str = "model_evaluation",
) -> Path:
    paths.reports.mkdir(parents=True, exist_ok=True)
    destination = paths.reports / f"{name}.md"
    destination.write_text(report, encoding="utf-8")
    (paths.reports / f"{name}.json").write_text(
        json.dumps(metrics, indent=2, default=str), encoding="utf-8"
    )
    return destination
