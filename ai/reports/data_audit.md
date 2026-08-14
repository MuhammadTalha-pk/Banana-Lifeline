# Dataset Audit — Banana Leaf Corpus

_Generated 2026-08-14 04:11 UTC by `banana audit`._

## Verdict

The published train/val/test split is **contaminated and unusable for honest evaluation**.
**622 of 1033 held-out images (60%)
have a near-identical twin in the training set.**

Any accuracy measured on this split is substantially memorisation.

## How the contamination got there

440 of 2636 files carry a filename where digits were
replaced by the letter `P` — `2P2512P5_161415.jpg` sitting beside `20251205_161415.jpg`.
A find-and-replace duplicated the image library, and **the split was performed afterwards**,
so copies of one photo scattered into different splits:

| Split | Corrupted-name files |
|---|---|
| train | 130 |
| val | 167 |
| test | 143 |

## Why content hashing did not catch it

| Check | Result |
|---|---|
| Files | 2636 |
| Unique MD5 hashes | **2636** |
| Unique scenes (perceptual clusters) | **1840** |

The copies were re-encoded as they were written, so every file is byte-unique and **MD5
deduplication reports the corpus perfectly clean**. Perceptual hashing collapses the same
2636 files into 1840 genuine scenes — about 30% of
the corpus is redundant.

Clustering: dHash (8×8,
64-bit), union-find over Hamming distance
≤ 5.

## Leakage

| Measure | Value |
|---|---|
| Scenes spanning more than one split | 481 |
| Files belonging to those scenes | 1221 |
| Holdout images with a train twin | **622 / 1033 (60%)** |

## Label conflicts

**18 scenes are labelled as more than one disease.** The same
photograph appears under two different diagnoses, so at least one copy is wrong — and the
confusion is concentrated in panama vs sigatoka, the model's hardest distinction.

| Cluster | Files | Labels present |
|---|---|---|
| 348 | `train/panama/20251205_120956_result_result.jpg`, `val/panama/20251205_120956_result_result.jpg`, `val/sigatoka/2P251205_120956_result_result.jpg`, `test/sigatoka/2P251205_120956_result_result.jpg` | **panama vs sigatoka** |
| 354 | `train/panama/20251205_121505_result_result.jpg`, `train/sigatoka/20251205_121503_result_result.jpg`, `val/panama/20251205_121505_result_result.jpg` | **panama vs sigatoka** |
| 366 | `train/panama/20251205_123011_result_result.jpg`, `val/panama/20251205_123011_result_result.jpg`, `val/sigatoka/2P251205_123011_result_result.jpg`, `test/panama/20251205_123011_result_result.jpg` | **panama vs sigatoka** |
| 381 | `train/panama/20251205_124351_result_result.jpg`, `test/sigatoka/2P251205_124351_result_result.jpg` | **panama vs sigatoka** |
| 382 | `train/panama/20251205_124408_result_result.jpg`, `val/sigatoka/2P251205_124408_result_result.jpg` | **panama vs sigatoka** |
| 405 | `train/panama/20251205_161438_result_result.jpg`, `test/sigatoka/2P251205_161438_result_result.jpg` | **panama vs sigatoka** |
| … | _12 more clusters_ | |

These scenes are quarantined to `data/review/` and excluded from training until an
agricultural expert rules on them.

## Class balance

| Class | Files | Distinct scenes |
|---|---|---|
| healthy | 636 | 391 |
| panama | 497 | 287 |
| sigatoka | 1503 | 1180 |

Measured in scenes rather than files, **panama is the smallest class** — and it is both the
most economically severe disease and the hardest to diagnose from a leaf photo. This is why
macro-F1 and per-class recall, not accuracy, are the reported metrics.

## Corpus properties

| Property | Value |
|---|---|
| Longest side (min / median / max) | 2458 / 2560 / 5223 px |
| Total size | 3.73 GB |
| Unreadable files | 0 |

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
