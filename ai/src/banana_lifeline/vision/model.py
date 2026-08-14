"""Model construction and checkpoint handling.

A ``timm`` CNN backbone with a fresh classification head. Two things here are load-bearing
beyond the architecture choice:

* **Feature extraction is exposed**, because Phase 3's Mahalanobis OOD detector needs
  penultimate features, not logits.
* **Checkpoints carry their own config**, so a saved model can always be rebuilt exactly.
  A checkpoint that needs a matching YAML file to be interpretable is a checkpoint that
  becomes useless the moment the config drifts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from banana_lifeline.config import CLASS_NAMES, ModelConfig, TrainConfig


@dataclass(slots=True)
class LoadedModel:
    """A restored model plus everything needed to interpret it."""

    model: Any
    train_config: TrainConfig
    class_names: tuple[str, ...]
    temperature: float
    metrics: dict[str, Any]
    abstain_threshold: float | None = None

    @property
    def is_calibrated(self) -> bool:
        """Whether a fitted temperature was written back after training.

        Calibration is fitted post-training, so a freshly saved checkpoint carries the
        placeholder ``temperature == 1.0``. Consuming that as if it were calibrated yields
        overconfident scores and makes any abstain threshold meaningless -- so callers that
        depend on confidence must check this rather than assume.
        """
        return self.temperature != 1.0 and self.abstain_threshold is not None


def build_model(cfg: ModelConfig, num_classes: int = len(CLASS_NAMES)) -> Any:
    """Create the backbone with a fresh head sized to our classes."""
    import timm

    return timm.create_model(
        cfg.architecture,
        pretrained=cfg.pretrained,
        num_classes=num_classes,
        drop_rate=cfg.drop_rate,
        drop_path_rate=cfg.drop_path_rate,
    )


def parameter_groups(model: Any, base_lr: float, backbone_scale: float) -> list[dict[str, Any]]:
    """Split parameters so the pretrained trunk learns slower than the new head.

    The head starts random and needs to move fast; the backbone already encodes useful
    texture filters and mostly needs nudging. One global learning rate either destroys the
    pretrained features or leaves the head undertrained.
    """
    classifier = model.get_classifier()
    head_ids = {id(p) for p in classifier.parameters()}

    head_params = [p for p in model.parameters() if id(p) in head_ids and p.requires_grad]
    backbone_params = [p for p in model.parameters() if id(p) not in head_ids and p.requires_grad]

    return [
        {"params": backbone_params, "lr": base_lr * backbone_scale, "name": "backbone"},
        {"params": head_params, "lr": base_lr, "name": "head"},
    ]


def extract_features(model: Any, images: Any) -> Any:
    """Penultimate-layer features, pooled. Used by the OOD detector in Phase 3."""
    features = model.forward_features(images)
    return model.forward_head(features, pre_logits=True)


def save_checkpoint(
    path: Path,
    model: Any,
    train_config: TrainConfig,
    metrics: dict[str, Any],
    *,
    temperature: float = 1.0,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a self-describing checkpoint.

    The config and class order travel with the weights so inference never has to guess which
    YAML produced them, and so a label-order change can never silently remap predictions.
    """
    import torch

    payload = {
        "state_dict": model.state_dict(),
        "train_config": train_config.model_dump(),
        "class_names": list(CLASS_NAMES),
        "temperature": temperature,
        "metrics": metrics,
    }
    if extra:
        payload.update(extra)

    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def load_checkpoint(path: Path, *, device: str = "cpu") -> LoadedModel:
    """Rebuild a model exactly as it was saved."""
    import torch

    if not path.is_file():
        raise FileNotFoundError(f"No checkpoint at {path}")

    payload = torch.load(path, map_location=device, weights_only=False)
    train_config = TrainConfig.model_validate(payload["train_config"])
    class_names = tuple(payload.get("class_names", CLASS_NAMES))

    if class_names != CLASS_NAMES:
        raise ValueError(
            f"Checkpoint class order {class_names} does not match the current "
            f"canonical order {CLASS_NAMES}. Predictions would be silently remapped."
        )

    model = build_model(train_config.model, num_classes=len(class_names))
    model.load_state_dict(payload["state_dict"])
    model.to(device)
    model.eval()

    threshold = payload.get("abstain_threshold")
    return LoadedModel(
        model=model,
        train_config=train_config,
        class_names=class_names,
        temperature=float(payload.get("temperature", 1.0)),
        metrics=payload.get("metrics", {}),
        abstain_threshold=float(threshold) if threshold is not None else None,
    )


def attach_calibration(
    path: Path,
    *,
    temperature: float,
    abstain_threshold: float,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a fitted temperature and abstain threshold into an existing checkpoint.

    Training cannot do this itself: calibration is fitted on validation logits only once
    training has finished. Leaving it in a side report instead means every consumer of the
    checkpoint silently gets uncalibrated confidence, so it is written back to the file that
    actually travels.
    """
    import torch

    payload = torch.load(path, map_location="cpu", weights_only=False)
    payload["temperature"] = float(temperature)
    payload["abstain_threshold"] = float(abstain_threshold)
    if extra:
        payload.update(extra)
    torch.save(payload, path)
