"""Augmentation pipelines.

The design rule that matters here: **colour is signal, not noise.** Leaf yellowing is what
separates healthy from diseased, and the yellow/brown balance contributes to separating
sigatoka from panama. Standard augmentation presets treat hue as a nuisance variable to be
randomised away, which on this dataset manufactures wrong labels -- a hue-shifted sigatoka
leaf looks healthy but still carries the sigatoka label.

So: geometry is augmented freely, brightness and contrast moderately, saturation slightly,
and hue not at all.
"""

from __future__ import annotations

from typing import Any

from banana_lifeline.config import AugmentationConfig

# ImageNet statistics, matching the pretrained backbone's expectations.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


# --------------------------------------------------------------------------------------
# albumentations compatibility
#
# 1.4 renamed several constructors. We support both because 1.4+ pulls in a dependency
# that needs a C toolchain to build on Windows, so a Windows CPU box realistically runs
# 1.3.x while Colab and CI run 1.4+. Rather than pin everyone to the lowest version, the
# two call shapes are bridged here and nowhere else.
# --------------------------------------------------------------------------------------


def _is_modern(module: Any) -> bool:
    return tuple(int(p) for p in module.__version__.split(".")[:2]) >= (1, 4)


def _random_resized_crop(module: Any, size: int, scale_min: float, scale_max: float) -> Any:
    if _is_modern(module):
        return module.RandomResizedCrop(
            size=(size, size), scale=(scale_min, scale_max), ratio=(0.8, 1.25)
        )
    return module.RandomResizedCrop(
        height=size, width=size, scale=(scale_min, scale_max), ratio=(0.8, 1.25)
    )


def _coarse_dropout(module: Any, size: int, prob: float) -> Any:
    """Occlusion patches sized 5-15% of the frame, expressed for either API."""
    if _is_modern(module):
        return module.CoarseDropout(
            num_holes_range=(1, 6),
            hole_height_range=(0.05, 0.15),
            hole_width_range=(0.05, 0.15),
            p=prob,
        )
    return module.CoarseDropout(
        max_holes=6,
        max_height=int(size * 0.15),
        max_width=int(size * 0.15),
        min_holes=1,
        min_height=int(size * 0.05),
        min_width=int(size * 0.05),
        p=prob,
    )


def build_train_transform(image_size: int, cfg: AugmentationConfig) -> Any:
    """Training-time augmentation.

    ``RandomResizedCrop`` down to half the frame is deliberate: it forces the model to
    diagnose from lesion texture on a patch of leaf rather than from the overall silhouette
    of the plant. That matters because every photo in this corpus comes from one site on one
    day, so whole-frame shortcuts are abundantly available.
    """
    import albumentations as A
    from albumentations.pytorch import ToTensorV2

    if cfg.hue_shift > 0:
        raise ValueError(
            "hue_shift must be 0 for this dataset: leaf colour is the class signal, so "
            "randomising hue produces mislabelled training images."
        )

    return A.Compose(
        [
            _random_resized_crop(A, image_size, cfg.scale_min, cfg.scale_max),
            A.HorizontalFlip(p=cfg.horizontal_flip),
            A.VerticalFlip(p=cfg.vertical_flip),
            A.Rotate(limit=cfg.rotate_limit, border_mode=0, p=0.7),
            # Brightness and contrast vary hugely between a shaded understorey shot and one
            # in direct Punjab sun, so the model must be invariant to them.
            A.RandomBrightnessContrast(
                brightness_limit=cfg.brightness,
                contrast_limit=cfg.contrast,
                p=0.7,
            ),
            # hue is pinned to 0; only saturation and value move.
            A.HueSaturationValue(
                hue_shift_limit=0,
                sat_shift_limit=int(cfg.saturation * 100),
                val_shift_limit=10,
                p=0.3,
            ),
            # Farmers shoot one-handed, often in wind.
            A.MotionBlur(blur_limit=5, p=cfg.blur_prob),
            # Neighbouring leaves occlude the subject constantly in a real plantation.
            _coarse_dropout(A, image_size, cfg.coarse_dropout_prob),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]
    )


def build_eval_transform(image_size: int) -> Any:
    """Deterministic evaluation transform.

    Resize-then-centre-crop rather than a direct squash, so aspect ratio is preserved and
    lesions are not distorted. Must stay deterministic: a stochastic eval transform makes
    metrics irreproducible.
    """
    import albumentations as A
    from albumentations.pytorch import ToTensorV2

    return A.Compose(
        [
            A.SmallestMaxSize(max_size=int(image_size * 1.14)),
            A.CenterCrop(height=image_size, width=image_size),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]
    )


def build_background_ablation_transform(image_size: int) -> Any:
    """Aggressive centre crop, used to test for background shortcut learning.

    Every photo in this corpus shares a site, a date, and a sky. If the model is reading
    background rather than pathology, accuracy will hold up here (leaf still present, context
    removed) far worse than the headline number suggests -- or it will barely move, which is
    evidence the model is genuinely reading the leaf.
    """
    import albumentations as A
    from albumentations.pytorch import ToTensorV2

    return A.Compose(
        [
            A.SmallestMaxSize(max_size=image_size),
            A.CenterCrop(height=image_size // 2, width=image_size // 2),
            A.Resize(height=image_size, width=image_size),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]
    )
