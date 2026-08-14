"""Manifest-driven dataset access.

Loading is driven **only** by a manifest CSV. There is deliberately no
``ImageFolder``-style directory walk anywhere in this project: directory layout is what
encoded the contaminated split, and as long as no code reads it, the layout cannot silently
decide what a model trains on again.

``torch`` is imported lazily so the audit and split pipeline stays runnable on a laptop with
only the core dependencies installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from banana_lifeline.config import CLASS_NAMES, DataConfig, Paths

if TYPE_CHECKING:
    # torch lives only on the GPU box. Typing against ``object`` here keeps the data pipeline
    # importable -- and typecheckable -- on a laptop with no training stack installed.
    Dataset = object
else:  # pragma: no cover - resolved at import time, not a branch worth testing
    try:
        from torch.utils.data import Dataset
    except ImportError:
        Dataset = object

LABEL_TO_INDEX: dict[str, int] = {name: i for i, name in enumerate(CLASS_NAMES)}
INDEX_TO_LABEL: dict[int, str] = dict(enumerate(CLASS_NAMES))


def load_manifest(path: Path, split: str | None = None) -> pd.DataFrame:
    """Read a manifest CSV, optionally filtered to one split."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Manifest not found at {path}. Run `banana split` to generate the manifests."
        )
    frame = pd.read_csv(path)
    missing = {"relpath", "cache_path", "cluster_id", "label", "split"} - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
    if split is not None:
        frame = frame[frame["split"] == split].reset_index(drop=True)
        if frame.empty:
            raise ValueError(f"No rows for split={split!r} in {path}")
    return frame


def manifest_path(paths: Paths, variant: str) -> Path:
    """Resolve a manifest by variant name (``clean``, ``original``, ``quarantine``)."""
    return paths.manifests / f"splits_{variant}.csv"


def class_weights(frame: pd.DataFrame) -> list[float]:
    """Inverse-frequency weights in canonical class order.

    Sigatoka outnumbers panama roughly 4:1, so an unweighted model can score well while
    effectively ignoring the class that matters most.
    """
    counts = frame["label"].value_counts()
    total = float(len(frame))
    return [total / (len(CLASS_NAMES) * float(counts.get(name, 1))) for name in CLASS_NAMES]


def sample_weights(frame: pd.DataFrame) -> list[float]:
    """Per-row weights for a ``WeightedRandomSampler``."""
    weights = class_weights(frame)
    return [weights[LABEL_TO_INDEX[str(label)]] for label in frame["label"]]


class BananaLeafDataset(Dataset):
    """Images plus integer labels, resolved from the resized cache.

    Each item also carries its ``cluster_id`` so that evaluation code can group predictions
    by scene and report per-scene as well as per-image metrics.
    """

    def __init__(
        self,
        manifest: pd.DataFrame,
        paths: Paths,
        data_cfg: DataConfig,
        transform: Any | None = None,
        *,
        use_cache: bool = True,
    ) -> None:
        self.frame = manifest.reset_index(drop=True)
        self.paths = paths
        self.transform = transform
        self.use_cache = use_cache
        self.raw_root = data_cfg.resolved_raw_root(paths)

        unknown = set(self.frame["label"].unique()) - set(CLASS_NAMES)
        if unknown:
            raise ValueError(f"Manifest contains labels outside the class list: {sorted(unknown)}")

    def __len__(self) -> int:
        return len(self.frame)

    def resolve_path(self, index: int) -> Path:
        row = self.frame.iloc[index]
        if self.use_cache:
            cached = self.paths.cache / str(row["cache_path"])
            if cached.is_file():
                return cached
        return self.raw_root / str(row["relpath"])

    def __getitem__(self, index: int) -> dict[str, Any]:
        import numpy as np
        from PIL import Image

        row = self.frame.iloc[index]
        with Image.open(self.resolve_path(index)) as image:
            array = np.asarray(image.convert("RGB"))

        if self.transform is not None:
            array = self.transform(image=array)["image"]

        return {
            "image": array,
            "label": LABEL_TO_INDEX[str(row["label"])],
            "cluster_id": int(row["cluster_id"]),
            "relpath": str(row["relpath"]),
        }
