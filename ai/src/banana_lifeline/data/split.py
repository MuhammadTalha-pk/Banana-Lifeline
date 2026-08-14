"""Group-aware dataset splitting and conflict quarantine.

Two rules govern this module:

1. **A scene never spans two splits.** Assignment happens at ``cluster_id`` granularity, so
   every copy of a photograph lands together. Splitting on filenames is what produced the
   59% leak in the raw corpus.
2. **Contested labels do not train.** Scenes whose copies disagree about the disease are
   quarantined for expert review rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from banana_lifeline.config import DataConfig, Paths
from banana_lifeline.data.verdicts import VerdictSet

MANIFEST_COLUMNS = [
    "relpath",
    "filename",
    "cache_path",
    "cluster_id",
    "label",
    "split",
    "split_original",
]


@dataclass(slots=True)
class SplitSummary:
    """What the split produced, for logging and for the audit trail."""

    n_scenes: int
    n_files: int
    n_quarantined_scenes: int
    n_quarantined_files: int
    files_per_split: dict[str, int]
    scenes_per_split: dict[str, int]
    class_matrix: pd.DataFrame


def resolve_cluster_labels(
    frame: pd.DataFrame,
    verdicts: VerdictSet | None = None,
) -> tuple[pd.Series, list[int]]:
    """Assign one label per scene; return ``(labels, contested_cluster_ids)``.

    Uncontested scenes take their unanimous label. Contested scenes get ``pd.NA`` -- they are
    quarantined, never majority-voted. A majority vote here would launder a labelling error
    into training data on exactly the panama/sigatoka boundary the model struggles with most.

    When ``verdicts`` are supplied, an expert ruling overrides the quarantine: scenes given a
    class re-enter training under that label, and scenes ruled ``discard`` stay out.
    """
    per_cluster = frame.groupby("cluster_id")["label_original"].agg(["nunique", "first"])
    contested = sorted(int(c) for c in per_cluster[per_cluster["nunique"] > 1].index)

    labels = per_cluster["first"].copy()
    labels[per_cluster["nunique"] > 1] = pd.NA

    if verdicts is not None:
        for cluster_id, label in verdicts.labels.items():
            if cluster_id in labels.index:
                labels.at[cluster_id] = label

    return labels, contested


def _greedy_balanced_assignment(
    cluster_sizes: dict[int, int],
    ratios: dict[str, float],
    rng: np.random.Generator,
) -> dict[int, str]:
    """Distribute clusters across splits, hitting file-count targets without breaking scenes.

    Straight ratio-splitting of *clusters* skews file counts, because scene sizes here run
    from 1 to 15 images. Instead: shuffle, walk largest-first, and drop each scene into
    whichever split is furthest below its target share of files. Deterministic under a seed.
    """
    total_files = sum(cluster_sizes.values())
    targets = {split: ratio * total_files for split, ratio in ratios.items()}
    assigned_files = dict.fromkeys(ratios, 0)
    assignment: dict[int, str] = {}

    cluster_ids = np.array(sorted(cluster_sizes), dtype=np.int64)
    rng.shuffle(cluster_ids)
    # Largest scenes first: place the lumpy items while there is still room to compensate.
    ordered = sorted(cluster_ids.tolist(), key=lambda c: -cluster_sizes[c])

    for cluster_id in ordered:
        deficits = {
            split: (targets[split] - assigned_files[split]) / max(targets[split], 1e-9)
            for split in ratios
        }
        chosen = max(deficits, key=lambda s: deficits[s])
        assignment[cluster_id] = chosen
        assigned_files[chosen] += cluster_sizes[cluster_id]

    return assignment


def build_clean_split(
    frame: pd.DataFrame,
    data_cfg: DataConfig,
    verdicts: VerdictSet | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Produce ``(clean_manifest, quarantine_manifest)`` from a fingerprinted corpus.

    Stratification is per class: each class is balanced across splits independently, so
    panama's 287 scenes are not left to chance by a global shuffle.
    """
    usable = frame[frame["error"].isna()].copy()
    cluster_labels, _contested = resolve_cluster_labels(usable, verdicts)

    usable["label"] = usable["cluster_id"].map(cluster_labels)
    quarantine = usable[usable["label"].isna()].copy()
    trainable = usable[usable["label"].notna()].copy()

    ratios = {
        "train": data_cfg.split.train,
        "val": data_cfg.split.val,
        "test": data_cfg.split.test,
    }
    rng = np.random.default_rng(data_cfg.split.seed)

    assignment: dict[int, str] = {}
    for label in data_cfg.class_names:
        subset = trainable[trainable["label"] == label]
        if subset.empty:
            continue
        # pandas types group keys as Hashable; cluster ids are ints by construction.
        sizes = {int(cast(int, k)): int(v) for k, v in subset.groupby("cluster_id").size().items()}
        assignment.update(_greedy_balanced_assignment(sizes, ratios, rng))

    trainable["split"] = trainable["cluster_id"].map(assignment)
    quarantine["split"] = "quarantine"
    quarantine["label"] = pd.NA

    if trainable["split"].isna().any():
        missing = int(trainable["split"].isna().sum())
        raise RuntimeError(f"{missing} files were left unassigned by the split")

    return trainable, quarantine


def build_original_split(frame: pd.DataFrame, quarantine: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the contaminated on-disk split, minus the quarantined scenes.

    Quarantined scenes are dropped from *both* manifests on purpose. The comparison run has
    to isolate one variable -- split contamination -- so label noise must be held constant
    across the two. Otherwise a difference in accuracy has two possible causes and proves
    nothing.
    """
    usable = frame[frame["error"].isna()].copy()
    quarantined_clusters = set(quarantine["cluster_id"].dropna().tolist())
    original = usable[~usable["cluster_id"].isin(quarantined_clusters)].copy()
    original["label"] = original["label_original"]
    original["split"] = original["split_original"]
    return original


def to_manifest(frame: pd.DataFrame, data_cfg: DataConfig, paths: Paths) -> pd.DataFrame:
    """Normalise a split frame into the canonical manifest schema."""
    root = data_cfg.resolved_raw_root(paths)
    out = frame.copy()
    out["relpath"] = out["relpath"].map(
        lambda p: Path(p).resolve().relative_to(root.resolve()).as_posix()
    )
    # Cache filenames must be unique across the corpus: the 0->P bug means the same basename
    # occurs in several class folders, so the relative path is flattened into the name.
    out["cache_path"] = out["relpath"].map(lambda r: r.replace("/", "__"))
    return out[MANIFEST_COLUMNS].sort_values(["split", "label", "relpath"]).reset_index(drop=True)


def summarise(clean: pd.DataFrame, quarantine: pd.DataFrame) -> SplitSummary:
    matrix = (
        clean.pivot_table(index="label", columns="split", values="relpath", aggfunc="count")
        .fillna(0)
        .astype(int)
    )
    return SplitSummary(
        n_scenes=int(clean["cluster_id"].nunique()),
        n_files=len(clean),
        n_quarantined_scenes=int(quarantine["cluster_id"].nunique()),
        n_quarantined_files=len(quarantine),
        files_per_split={
            str(k): int(v) for k, v in clean["split"].value_counts().sort_index().items()
        },
        scenes_per_split={
            str(k): int(v)
            for k, v in clean.groupby("split")["cluster_id"].nunique().sort_index().items()
        },
        class_matrix=matrix,
    )


def verify_no_leakage(manifest: pd.DataFrame) -> None:
    """Fail loudly if any scene spans two splits. Called after every split generation."""
    spans = manifest.groupby("cluster_id")["split"].nunique()
    offenders = spans[spans > 1]
    if len(offenders) > 0:
        raise AssertionError(
            f"{len(offenders)} scenes span multiple splits (e.g. cluster "
            f"{int(offenders.index[0])}). The split is leaking."
        )
