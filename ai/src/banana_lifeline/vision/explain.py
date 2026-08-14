"""Grad-CAM overlays — visual evidence of what the model actually looks at.

This is not decoration. Every photograph in the corpus was taken at one site on one day, so
sky, soil, and neighbouring foliage are nearly constant within a class and a model can score
well by reading them. The background ablation in ``evaluate.py`` measures that numerically;
these overlays show it, which is what makes it arguable in a review.

What to look for: heat concentrated on lesions and leaf tissue is the model working. Heat on
sky, soil, or the photographer's hand means the score is borrowed from context and will not
survive a different farm.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from banana_lifeline.config import CLASS_NAMES, DataConfig, Paths, TrainConfig


def _target_layer(model: Any) -> Any:
    """Last convolutional stage, where spatial detail still exists.

    Works across the CNN backbones we might swap between (EfficientNet, MobileNet, ResNet)
    rather than hardcoding one architecture's attribute name.
    """
    for attribute in ("conv_head", "layer4", "blocks", "features"):
        module = getattr(model, attribute, None)
        if module is None:
            continue
        if hasattr(module, "__getitem__"):
            try:
                return module[-1]
            except (IndexError, TypeError):
                return module
        return module

    convolutions = [m for m in model.modules() if m.__class__.__name__ == "Conv2d"]
    if not convolutions:
        raise RuntimeError("Could not locate a convolutional layer for Grad-CAM")
    return convolutions[-1]


def generate_overlays(
    model: Any,
    manifest: pd.DataFrame,
    train_cfg: TrainConfig,
    data_cfg: DataConfig,
    paths: Paths,
    *,
    output_dir: Path | None = None,
    per_class: int = 4,
    seed: int = 0,
) -> Path:
    """Write Grad-CAM overlays for a stratified sample, plus a contact sheet.

    Samples correct and incorrect predictions separately: the failures are where shortcut
    learning is easiest to spot.
    """
    import cv2
    import torch
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    from banana_lifeline.data.dataset import LABEL_TO_INDEX, BananaLeafDataset
    from banana_lifeline.vision.transforms import (
        IMAGENET_MEAN,
        IMAGENET_STD,
        build_eval_transform,
    )

    destination = output_dir or (paths.reports / "gradcam")
    destination.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device).eval()

    rng = np.random.default_rng(seed)
    sampled = pd.concat(
        [
            group.sample(min(per_class, len(group)), random_state=int(rng.integers(1 << 30)))
            for _, group in manifest.groupby("label")
        ]
    ).reset_index(drop=True)

    dataset = BananaLeafDataset(
        sampled, paths, data_cfg, transform=build_eval_transform(train_cfg.image_size)
    )
    cam = GradCAM(model=model, target_layers=[_target_layer(model)])

    written: list[dict[str, Any]] = []
    for index in range(len(dataset)):
        item = dataset[index]
        tensor = item["image"].unsqueeze(0).to(device)

        with torch.no_grad():
            predicted = int(model(tensor).argmax(dim=1).item())

        heatmap = cam(input_tensor=tensor, targets=[ClassifierOutputTarget(predicted)])[0]

        # Undo normalisation to recover a viewable image.
        image = item["image"].permute(1, 2, 0).cpu().numpy()
        image = np.clip(image * np.array(IMAGENET_STD) + np.array(IMAGENET_MEAN), 0, 1)

        heatmap_u8 = (255 * heatmap).astype(np.uint8)
        colour = cv2.applyColorMap(heatmap_u8, cv2.COLORMAP_JET)[:, :, ::-1] / 255.0
        overlay = (255 * np.clip(0.5 * colour + 0.5 * image, 0, 1)).astype(np.uint8)

        true_label = str(sampled.iloc[index]["label"])
        predicted_label = CLASS_NAMES[predicted]
        status = "ok" if LABEL_TO_INDEX[true_label] == predicted else "WRONG"
        filename = f"{status}_{true_label}_as_{predicted_label}_{index:03d}.jpg"

        cv2.imwrite(str(destination / filename), overlay[:, :, ::-1])
        written.append(
            {
                "file": filename,
                "true": true_label,
                "predicted": predicted_label,
                "correct": status == "ok",
                "relpath": item["relpath"],
            }
        )

    pd.DataFrame(written).to_csv(destination / "index.csv", index=False)
    return destination
