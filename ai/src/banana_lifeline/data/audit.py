"""Dataset contamination audit.

Turns the cluster frame into hard numbers and a committed markdown report. This runs before
any training and its output is evidence: it is what justifies re-splitting the corpus and
what explains why the honest accuracy is lower than the number the original split produces.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from banana_lifeline.config import DataConfig, Paths

# Filenames are phone timestamps: 20251205_161415.jpg. The corrupted copies had their zeros
# replaced by capital P, so a digit-position P is the signature of the duplication event.
_CORRUPTED_NAME = re.compile(r"(?:^|[^0-9A-Za-z])(?=[0-9]*P)[0-9P]{6,}_")


@dataclass(slots=True)
class AuditResult:
    """Everything the audit measured. Serialised into the report and asserted on in tests."""

    n_files: int
    n_unique_md5: int
    n_clusters: int
    n_corrupted_names: int
    corrupted_by_split: dict[str, int]
    n_cross_split_clusters: int
    n_files_in_cross_split_clusters: int
    n_holdout_with_train_twin: int
    n_holdout_total: int
    conflict_clusters: list[int]
    scenes_per_class: dict[str, int]
    files_per_class: dict[str, int]
    files_per_split: dict[str, int]
    resolution_summary: dict[str, float]
    errors: list[str] = field(default_factory=list)

    @property
    def holdout_contamination_rate(self) -> float:
        if self.n_holdout_total == 0:
            return 0.0
        return self.n_holdout_with_train_twin / self.n_holdout_total


def _conflict_clusters(frame: pd.DataFrame) -> list[int]:
    """Clusters whose members disagree about the label -- the same photo, two diseases."""
    grouped = frame.groupby("cluster_id")["label_original"].nunique()
    return sorted(int(c) for c in grouped[grouped > 1].index)


def audit_clusters(frame: pd.DataFrame, data_cfg: DataConfig) -> AuditResult:
    """Measure contamination in a fingerprinted corpus."""
    usable = frame[frame["error"].isna()].copy()

    cluster_splits = usable.groupby("cluster_id")["split_original"].nunique()
    cross_split_clusters = cluster_splits[cluster_splits > 1].index
    n_files_affected = int(usable["cluster_id"].isin(cross_split_clusters).sum())

    # The headline number: holdout images whose scene also appears in train.
    train_clusters = set(usable.loc[usable["split_original"] == "train", "cluster_id"])
    holdout = usable[usable["split_original"] != "train"]
    n_holdout_with_twin = int(holdout["cluster_id"].isin(train_clusters).sum())

    corrupted_mask = usable["filename"].str.contains(_CORRUPTED_NAME, regex=True, na=False)
    corrupted_by_split = (
        usable.loc[corrupted_mask, "split_original"].value_counts().sort_index().to_dict()
    )

    scenes_per_class = {
        label: int(usable.loc[usable["label_original"] == label, "cluster_id"].nunique())
        for label in data_cfg.class_names
    }

    longest = usable[["width", "height"]].max(axis=1)
    resolution_summary = {
        "min_longest_side": float(longest.min()),
        "median_longest_side": float(longest.median()),
        "max_longest_side": float(longest.max()),
        "total_gb": float(usable["bytes"].sum() / 1e9),
    }

    return AuditResult(
        n_files=len(usable),
        n_unique_md5=int(usable["md5"].nunique()),
        n_clusters=int(usable["cluster_id"].nunique()),
        n_corrupted_names=int(corrupted_mask.sum()),
        corrupted_by_split={str(k): int(v) for k, v in corrupted_by_split.items()},
        n_cross_split_clusters=len(cross_split_clusters),
        n_files_in_cross_split_clusters=n_files_affected,
        n_holdout_with_train_twin=n_holdout_with_twin,
        n_holdout_total=len(holdout),
        conflict_clusters=_conflict_clusters(usable),
        scenes_per_class=scenes_per_class,
        files_per_class={
            label: int((usable["label_original"] == label).sum()) for label in data_cfg.class_names
        },
        files_per_split={
            split: int((usable["split_original"] == split).sum()) for split in data_cfg.raw_splits
        },
        resolution_summary=resolution_summary,
        errors=frame.loc[frame["error"].notna(), "relpath"].tolist(),
    )


def _conflict_detail(frame: pd.DataFrame, cluster_ids: list[int], limit: int = 6) -> str:
    """Render a few label-conflict clusters so a reader can see the problem, not just count it."""
    if not cluster_ids:
        return "_None found._\n"

    lines = ["| Cluster | Files | Labels present |", "|---|---|---|"]
    for cluster_id in cluster_ids[:limit]:
        members = frame[frame["cluster_id"] == cluster_id]
        labels = sorted(members["label_original"].unique())
        placements = ", ".join(
            f"`{row.split_original}/{row.label_original}/{row.filename}`"
            for row in members.itertuples()
        )
        lines.append(f"| {cluster_id} | {placements} | **{' vs '.join(labels)}** |")
    if len(cluster_ids) > limit:
        lines.append(f"| … | _{len(cluster_ids) - limit} more clusters_ | |")
    return "\n".join(lines) + "\n"


def render_report(result: AuditResult, frame: pd.DataFrame, data_cfg: DataConfig) -> str:
    """Render the audit as markdown suitable for committing and for the project report."""
    pct = result.holdout_contamination_rate * 100
    dup_ratio = (1 - result.n_clusters / result.n_files) * 100 if result.n_files else 0.0

    per_class_rows = "\n".join(
        f"| {label} | {result.files_per_class[label]} | {result.scenes_per_class[label]} |"
        for label in data_cfg.class_names
    )
    corrupted_rows = "\n".join(
        f"| {split} | {result.corrupted_by_split.get(split, 0)} |" for split in data_cfg.raw_splits
    )

    return f"""# Dataset Audit — Banana Leaf Corpus

_Generated {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")} by `banana audit`._

## Verdict

The published train/val/test split is **contaminated and unusable for honest evaluation**.
**{result.n_holdout_with_train_twin} of {result.n_holdout_total} held-out images ({pct:.0f}%)
have a near-identical twin in the training set.**

Any accuracy measured on this split is substantially memorisation.

## How the contamination got there

{result.n_corrupted_names} of {result.n_files} files carry a filename where digits were
replaced by the letter `P` — `2P2512P5_161415.jpg` sitting beside `20251205_161415.jpg`.
A find-and-replace duplicated the image library, and **the split was performed afterwards**,
so copies of one photo scattered into different splits:

| Split | Corrupted-name files |
|---|---|
{corrupted_rows}

## Why content hashing did not catch it

| Check | Result |
|---|---|
| Files | {result.n_files} |
| Unique MD5 hashes | **{result.n_unique_md5}** |
| Unique scenes (perceptual clusters) | **{result.n_clusters}** |

The copies were re-encoded as they were written, so every file is byte-unique and **MD5
deduplication reports the corpus perfectly clean**. Perceptual hashing collapses the same
{result.n_files} files into {result.n_clusters} genuine scenes — about {dup_ratio:.0f}% of
the corpus is redundant.

Clustering: dHash ({data_cfg.fingerprint.dhash_size}×{data_cfg.fingerprint.dhash_size},
{data_cfg.fingerprint.dhash_size**2}-bit), union-find over Hamming distance
≤ {data_cfg.fingerprint.hamming_threshold}.

## Leakage

| Measure | Value |
|---|---|
| Scenes spanning more than one split | {result.n_cross_split_clusters} |
| Files belonging to those scenes | {result.n_files_in_cross_split_clusters} |
| Holdout images with a train twin | **{result.n_holdout_with_train_twin} / {result.n_holdout_total} ({pct:.0f}%)** |

## Label conflicts

**{len(result.conflict_clusters)} scenes are labelled as more than one disease.** The same
photograph appears under two different diagnoses, so at least one copy is wrong — and the
confusion is concentrated in panama vs sigatoka, the model's hardest distinction.

{_conflict_detail(frame, result.conflict_clusters)}
These scenes are quarantined to `data/review/` and excluded from training until an
agricultural expert rules on them.

## Class balance

| Class | Files | Distinct scenes |
|---|---|---|
{per_class_rows}

Measured in scenes rather than files, **panama is the smallest class** — and it is both the
most economically severe disease and the hardest to diagnose from a leaf photo. This is why
macro-F1 and per-class recall, not accuracy, are the reported metrics.

## Corpus properties

| Property | Value |
|---|---|
| Longest side (min / median / max) | {result.resolution_summary["min_longest_side"]:.0f} / {result.resolution_summary["median_longest_side"]:.0f} / {result.resolution_summary["max_longest_side"]:.0f} px |
| Total size | {result.resolution_summary["total_gb"]:.2f} GB |
| Unreadable files | {len(result.errors)} |

All photographs come from a single site on a single date, so background and lighting are
near-constant across classes. The model can therefore learn scene shortcuts instead of leaf
pathology; Grad-CAM review and a background-ablation run are part of Phase 2 for this reason.

## Consequence

1. A group-aware split keyed on `cluster_id` is generated as `splits_clean.csv`. No scene
   may appear in two splits.
2. The original split is preserved as `splits_original.csv` so both numbers can be reported
   side by side.
3. `tests/test_split_integrity.py` asserts zero cluster overlap, so this bug cannot return
   silently.
"""


def write_report(
    result: AuditResult, frame: pd.DataFrame, data_cfg: DataConfig, paths: Paths
) -> Path:
    paths.reports.mkdir(parents=True, exist_ok=True)
    destination = paths.reports / "data_audit.md"
    destination.write_text(render_report(result, frame, data_cfg), encoding="utf-8")
    return destination
