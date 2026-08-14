# Banana Lifeline — AI Layer

Disease classification and grounded agricultural guidance for Pakistani banana farmers.
This directory holds the AI layer only: the vision model, out-of-distribution rejection, the
RAG knowledge system, and answer generation. The Flutter app and FastAPI service consume it;
they are not built here.

## Status

| Phase | State |
|---|---|
| 0 — Foundation | Done |
| 1 — Data audit, leakage-free split, cache | **Done** |
| 2 — CNN classifier | Next |
| 3 — OOD rejection and abstain policy | Planned |
| 4 — RAG knowledge system | Planned |
| 5 — DeepSeek answer generation | Planned |

Full design: [PLAN.md](PLAN.md). Audit findings: [reports/data_audit.md](reports/data_audit.md).

## Read this before trusting any accuracy number

The dataset shipped with a broken train/val/test split. **622 of its 1,033 held-out images
(60%) have a near-identical twin in the training set.** The cause is visible in the
filenames: 440 files are `0`→`P` corrupted copies (`2P2512P5_161415.jpg` beside
`20251205_161415.jpg`), produced by a find-and-replace that ran *before* the split was made.

The copies were re-encoded when written, so **all 2,636 files are byte-unique and MD5
deduplication reports the corpus perfectly clean**. Perceptual hashing collapses them into
1,840 genuine scenes. 18 of those scenes are labelled as two different diseases at once.

Consequences baked into this codebase:

- Splitting happens on `cluster_id` (a perceptual scene), never on filename.
- Loading is manifest-driven. There is no `ImageFolder`-style directory walk anywhere — the
  directory layout is what encoded the bad split, so no code is allowed to read it.
- `tests/test_split_integrity.py` fails the build if any scene ever spans two splits.
- The contaminated split is preserved as `splits_original.csv` so both numbers can be
  reported side by side.

## Quickstart

Requires Python 3.11 (3.14 lacks wheels for the training stack).

```bash
make setup     # 3.11 venv + editable install
make data      # audit -> split -> cache  (~5 min, reads the corpus once)
make check     # ruff + mypy --strict + pytest
```

Or step by step:

```bash
banana audit    # fingerprint corpus, measure contamination, write reports/data_audit.md
banana split    # leakage-free manifests + comparison manifest + expert review sheet
banana cache    # 3.5 GB of phone photos -> 136 MB of 512px training images
banana status   # what exists on disk right now
```

## What Phase 1 produced

```
data/manifests/splits_clean.csv       2,584 files / 1,822 scenes, no scene spans two splits
data/manifests/splits_original.csv    the contaminated split, preserved for comparison
data/manifests/splits_quarantine.csv  52 files across 18 contested scenes
data/review/review.html               expert review sheet for those 18 scenes
data/cache/                           136 MB, 512px, EXIF-normalised
reports/data_audit.md                 the full finding
```

Clean split, by files and scenes:

| Split | Files | Scenes | healthy | panama | sigatoka |
|---|---|---|---|---|---|
| train | 1,808 | 1,280 | 442 | 329 | 1,037 |
| val | 388 | 271 | 95 | 71 | 222 |
| test | 388 | 271 | 95 | 71 | 222 |

## Open action — expert review

18 scenes are labelled as two diseases at once and are **excluded from training** until an
agronomist rules on them. Open `data/review/review.html` in a browser, record a verdict per
scene, and save the generated CSV as `data/review/verdicts.csv`.

This is the highest-value labelling work available: the conflicts sit on the panama/sigatoka
boundary, and panama is both the smallest class (287 scenes) and the most costly to
misdiagnose.

## Design notes worth knowing

**Metrics are macro-F1 and per-class recall, not accuracy.** Sigatoka outnumbers panama
roughly 4:1, so a model that ignores panama entirely still posts a strong accuracy figure.

**Training resolution is 384px, not the conventional 224.** Sigatoka's diagnostic signal is
fine speckling and thin dark streaks, and it is simply gone at 224.

**Hue jitter is excluded from augmentation.** Leaf yellowing *is* the class signal; shifting
hue destroys the label. Standard augmentation recipes get this wrong on plant disease data.

**Panama predictions do not assert.** Fusarium wilt is diagnosed from whole-plant collapse
and brown vascular tissue inside a cut pseudostem — signs a leaf close-up usually cannot
show. The system asks confirming questions a farmer can actually answer instead of stating a
diagnosis the image cannot support, and it never generates a chemical cure, because there
isn't one.

**All photographs come from one site on one date.** Background and lighting barely vary
between classes, so the model can learn scene shortcuts instead of leaf pathology. Grad-CAM
review and a background-ablation run are part of Phase 2 for exactly this reason.

## Layout

```
configs/            typed YAML, validated into pydantic models
src/banana_lifeline/
  config.py         paths and settings; BANANA_AI_ROOT overrides the root
  data/             fingerprint, audit, split, review, cache, dataset
  cli.py            the `banana` command
tests/              leakage regression tests
reports/            generated audit, model card, datasheet
runs/               per-run config, metrics, plots
```
