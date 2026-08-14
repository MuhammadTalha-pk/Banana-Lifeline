"""Typed configuration for the Banana Lifeline AI layer.

Every tunable lives in ``configs/*.yaml`` and is validated into a pydantic model here.
Nothing reads a magic constant out of the middle of a module, and nothing hardcodes an
absolute path -- the same config has to work on a Windows laptop and on a Google Cloud
GPU box where the repo sits somewhere else entirely.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

CLASS_NAMES: tuple[str, ...] = ("healthy", "panama", "sigatoka")
"""Canonical class order. Index in this tuple is the integer label, everywhere, always."""


def find_ai_root() -> Path:
    """Locate the ``ai/`` directory.

    Honours ``BANANA_AI_ROOT`` first so the training notebook can point at a clone in
    ``/home/jupyter/...`` without editing any config.
    """
    env = os.environ.get("BANANA_AI_ROOT")
    if env:
        root = Path(env).expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"BANANA_AI_ROOT points at a missing directory: {root}")
        return root

    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (candidate / "pyproject.toml").is_file() and (candidate / "src").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not locate the ai/ root. Set BANANA_AI_ROOT to the directory holding pyproject.toml."
    )


class Paths(BaseModel):
    """Filesystem layout, all derived from the ai/ root."""

    ai_root: Path = Field(default_factory=find_ai_root)

    @property
    def data(self) -> Path:
        return self.ai_root / "data"

    @property
    def manifests(self) -> Path:
        return self.data / "manifests"

    @property
    def cache(self) -> Path:
        return self.data / "cache"

    @property
    def review(self) -> Path:
        return self.data / "review"

    @property
    def corpus(self) -> Path:
        return self.data / "corpus"

    @property
    def reports(self) -> Path:
        return self.ai_root / "reports"

    @property
    def runs(self) -> Path:
        return self.ai_root / "runs"

    @property
    def configs(self) -> Path:
        return self.ai_root / "configs"


class FingerprintConfig(BaseModel):
    """Perceptual-hash settings used to collapse duplicate photos into scenes."""

    dhash_size: int = Field(8, ge=4, le=32, description="dHash grid; produces size*size bits.")
    hamming_threshold: int = Field(
        5,
        ge=0,
        description=(
            "Max bit distance for two images to count as the same scene. 5/64 was validated "
            "against this corpus: it catches the 0->P re-encoded copies without merging "
            "genuinely different leaves."
        ),
    )
    decode_scale: int = Field(
        4, ge=1, description="JPEG draft-mode downscale factor; speeds up decode ~10x."
    )


class SplitConfig(BaseModel):
    """Group-aware split settings. Ratios are over *scenes*, not files."""

    train: float = Field(0.70, gt=0, lt=1)
    val: float = Field(0.15, gt=0, lt=1)
    test: float = Field(0.15, gt=0, lt=1)
    seed: int = 1337

    @model_validator(mode="after")
    def _ratios_sum_to_one(self) -> SplitConfig:
        total = self.train + self.val + self.test
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"split ratios must sum to 1.0, got {total}")
        return self


class CacheConfig(BaseModel):
    """Pre-resized image cache. Turns 3.5 GB of phone photos into ~200 MB."""

    longest_side: int = Field(512, ge=64, description="Must exceed train resolution (384).")
    jpeg_quality: int = Field(90, ge=1, le=100)


class DataConfig(BaseModel):
    """Everything about getting from raw phone photos to a trustworthy manifest."""

    raw_root: Path = Field(
        Path("Banana_Leaf_Dataset"),
        description=(
            "Immutable raw corpus, relative to ai/ unless absolute. Never written to -- the "
            "on-disk train/val/test folders here are the *contaminated* split and are kept "
            "only so the comparison run can reproduce them."
        ),
    )
    raw_splits: tuple[str, ...] = ("train", "val", "test")
    class_names: tuple[str, ...] = CLASS_NAMES
    image_glob: str = "*.jpg"

    fingerprint: FingerprintConfig = Field(default_factory=FingerprintConfig)
    split: SplitConfig = Field(default_factory=SplitConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    def resolved_raw_root(self, paths: Paths) -> Path:
        return self.raw_root if self.raw_root.is_absolute() else paths.ai_root / self.raw_root


class AugmentationConfig(BaseModel):
    """Augmentation tuned to leaf pathology, not to ImageNet.

    The critical entry is ``hue_shift``, which is zero and should stay zero. Leaf yellowing
    *is* the class signal for both diseases -- shifting hue turns a sigatoka leaf into
    something that looks healthy while keeping the sigatoka label. Standard augmentation
    recipes enable it by default and quietly corrupt plant-disease training data.
    """

    horizontal_flip: float = Field(0.5, ge=0, le=1)
    vertical_flip: float = Field(0.5, ge=0, le=1, description="Leaves have no canonical up.")
    rotate_limit: int = Field(30, ge=0, le=180)
    scale_min: float = Field(0.5, gt=0, le=1, description="RandomResizedCrop lower bound.")
    scale_max: float = Field(1.0, gt=0, le=1)
    brightness: float = Field(0.2, ge=0, le=1)
    contrast: float = Field(0.2, ge=0, le=1)
    saturation: float = Field(0.1, ge=0, le=1, description="Kept small; colour carries signal.")
    hue_shift: float = Field(
        0.0,
        ge=0,
        le=0.5,
        description="MUST stay 0. Hue is the label here, not a nuisance variable.",
    )
    blur_prob: float = Field(0.2, ge=0, le=1, description="Simulates unsteady farmer photos.")
    coarse_dropout_prob: float = Field(0.2, ge=0, le=1)

    @model_validator(mode="after")
    def _scale_bounds(self) -> AugmentationConfig:
        if self.scale_min > self.scale_max:
            raise ValueError("scale_min must not exceed scale_max")
        return self


class ModelConfig(BaseModel):
    """Backbone selection. A genuine CNN, per the project spec."""

    architecture: str = Field("efficientnet_b0", description="Any timm model name.")
    pretrained: bool = True
    drop_rate: float = Field(0.3, ge=0, lt=1)
    drop_path_rate: float = Field(0.1, ge=0, lt=1, description="Stochastic depth.")


class OptimConfig(BaseModel):
    learning_rate: float = Field(3e-4, gt=0)
    backbone_lr_scale: float = Field(
        0.1,
        gt=0,
        le=1,
        description="Pretrained features need gentler updates than a fresh head.",
    )
    weight_decay: float = Field(1e-4, ge=0)
    warmup_epochs: int = Field(2, ge=0)
    label_smoothing: float = Field(0.05, ge=0, lt=1)


class TrainConfig(BaseModel):
    """Training recipe.

    Defaults target a **Colab T4**: 16 GB, Turing generation. That drives two choices --
    fp16 AMP rather than bf16 (Turing has no bf16 tensor cores), and a batch size that
    leaves headroom at 384px.
    """

    image_size: int = Field(
        384,
        ge=64,
        description=(
            "384, not the conventional 224. Sigatoka's diagnostic signal is fine speckling "
            "and thin dark streaks, and it is largely gone by 224."
        ),
    )
    batch_size: int = Field(24, ge=1, description="Fits 384px EfficientNet-B0 on a 16 GB T4.")
    grad_accum_steps: int = Field(1, ge=1)
    epochs: int = Field(30, ge=1)
    num_workers: int = Field(2, ge=0, description="Colab VMs have few cores.")
    seed: int = 1337

    amp: bool = True
    amp_dtype: str = Field(
        "float16",
        description="T4 is Turing: fp16 tensor cores, no bf16. Requires a GradScaler.",
    )
    channels_last: bool = True

    early_stop_patience: int = Field(8, ge=1)
    monitor_metric: str = Field(
        "macro_f1",
        description="Never accuracy: sigatoka outnumbers panama ~4:1.",
    )

    balanced_sampling: bool = Field(True, description="WeightedRandomSampler over classes.")
    model: ModelConfig = Field(default_factory=ModelConfig)
    optim: OptimConfig = Field(default_factory=OptimConfig)
    augment: AugmentationConfig = Field(default_factory=AugmentationConfig)

    @model_validator(mode="after")
    def _validate_amp(self) -> TrainConfig:
        if self.amp_dtype not in {"float16", "bfloat16"}:
            raise ValueError("amp_dtype must be float16 or bfloat16")
        return self

    @property
    def effective_batch_size(self) -> int:
        return self.batch_size * self.grad_accum_steps


def load_train_config(path: Path | None = None) -> TrainConfig:
    cfg_path = path or (get_paths().configs / "train.yaml")
    if not cfg_path.is_file():
        return TrainConfig()
    return TrainConfig.model_validate(load_yaml(cfg_path))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh) or {}
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a YAML mapping, got {type(loaded).__name__}")
    return loaded


@lru_cache(maxsize=1)
def get_paths() -> Paths:
    return Paths()


def load_data_config(path: Path | None = None) -> DataConfig:
    """Load ``configs/data.yaml``, falling back to defaults when it is absent."""
    cfg_path = path or (get_paths().configs / "data.yaml")
    if not cfg_path.is_file():
        return DataConfig()
    return DataConfig.model_validate(load_yaml(cfg_path))
