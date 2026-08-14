# Banana Lifeline — AI Layer Implementation Plan

## Context

Banana Lifeline helps Pakistani banana farmers identify plant disease from a phone photo and get trustworthy agricultural guidance. This plan covers **the AI layer only** — the CNN classifier, out-of-distribution rejection, the RAG knowledge system, and DeepSeek answer generation. Flutter app, FastAPI service, and Firebase are explicitly out of scope; the deliverable is a self-contained, importable Python package plus trained artifacts that a backend can later wrap.

The repo is currently near-empty: one commit, a `.gitignore`, a stub `README.md`, and `ai/Banana_Leaf_Dataset/` (2,636 JPEGs, 3.5 GB, three classes).

**The finding that shapes this plan.** An audit of that dataset found the train/val/test split is contaminated:

- 2,636 files collapse to **1,840 distinct scenes** (perceptual-hash clustering, Hamming ≤5).
- **611 of 1,033 val+test images (59%) have a near-twin in train.**
- Root cause: 440 files are `0`→`P` filename-corrupted copies (`2P2512P5_161415.jpg` beside `20251205_161415.jpg`). A find-and-replace duplicated the library and **the split was made afterwards**, scattering copies across train (130), val (167), test (143).
- MD5 finds **zero** exact duplicates — the copies were re-encoded, so any byte-level dedup check passes and reports the data clean.
- **18 clusters carry conflicting labels.** Photo `..._120956` appears as `train/panama`, `val/panama`, `val/sigatoka`, and `test/sigatoka` — the same photograph, two diseases.

Training on this split yields ~97–99% accuracy that is memorization and will not survive contact with real farmer photos. Everything below is built so that number cannot be reported by accident again.

**Secondary constraints found during the audit:**

| Constraint | Detail | Consequence |
|---|---|---|
| No GPU | `torch 2.12.1+cpu`, no CUDA, no `nvidia-smi` | Train on a **Google Cloud GPU**, driven from a `.ipynb` notebook |
| Python 3.14 | `torchvision`, `timm`, `sklearn`, `onnx` all missing | Pin a **Python 3.11** venv |
| Class imbalance | 1,180 sigatoka vs 391 healthy vs **287 panama** scenes | Macro-F1, not accuracy, is the metric |
| Huge images | 1920×2560 up to 5223×3917 | Pre-resized cache; raw dir stays read-only |
| Single-site capture | All photos one orchard, one day | Background shortcut risk — verify with Grad-CAM |
| Leaves only | Dir is `Banana_Leaf_Dataset`; spec promises "any part of the plant" | Fruit/pseudostem photos are OOD at launch |

**Confirmed decisions:** clean re-split *and* report both numbers · quarantine the 18 conflict clusters for expert review · panama predictions trigger a guided follow-up rather than a bare assertion.

---

## Guiding principle

Panama disease (Fusarium wilt) has **no chemical cure** and is diagnosed from whole-plant collapse and brown vascular tissue in a cut pseudostem — signs a single leaf close-up usually cannot show. A confident wrong answer here costs a farmer a crop. The system must therefore be able to say *"I am not sure"* and *"this photo cannot tell us"*, and must never invent a fungicide treatment for panama. Calibration, abstention, and OOD rejection are core features, not polish.

---

## Repository layout

Everything lands under `ai/`. `ai/Banana_Leaf_Dataset/` becomes **immutable raw input** — never modified, never split in place.

```
ai/
  pyproject.toml            # deps pinned, Python 3.11
  README.md                 # quickstart + honest results table
  Makefile                  # audit / split / train / eval / index targets
  configs/                  # data.yaml, train.yaml, rag.yaml, generation.yaml
  data/
    Banana_Leaf_Dataset/    # READ-ONLY raw
    manifests/              # clusters.csv, splits_clean.csv, splits_original.csv
    cache/                  # 512px pre-resized JPEGs
    review/                 # quarantined conflict clusters + review.html
    corpus/                 # RAG source documents
  src/banana_lifeline/
    data/       fingerprint.py  audit.py  split.py  cache.py  dataset.py
    vision/     model.py  train.py  evaluate.py  calibrate.py  ood.py  export.py
    rag/        sources.py  ingest.py  chunk.py  embed.py  index.py  retrieve.py  eval.py
    generation/ prompts.py  answer.py  followup.py  glossary.py
    pipeline.py             # image + question -> grounded answer (the public entry point)
    cli.py                  # typer CLI
  notebooks/01_train_gpu.ipynb   # thin driver for the Google Cloud GPU box
  reports/                  # audit report, model card, datasheet
  runs/                     # per-run configs, metrics, plots (gitignored except metrics)
  tests/
```

---

## Phase 0 — Foundation

Python 3.11 venv (3.14 lacks the wheels). Pinned deps: `torch`, `torchvision`, `timm`, `albumentations`, `scikit-learn`, `pandas`, `pydantic-settings`, `typer`, `qdrant-client`, `FlagEmbedding`, `openai` (DeepSeek is OpenAI-API-compatible), `pytest`, `ruff`, `mypy`.

Config via YAML → `pydantic` models, so every knob is typed and validated. Every training run writes `runs/<timestamp>/` containing the resolved config, git SHA, `metrics.json`, and plots — a run is reproducible from its own directory.

GitHub Actions: `ruff` + `mypy` + `pytest` on push.

---

## Phase 1 — Data audit and honest split

**This is the phase that protects every number downstream.** Ship it before any training.

`data/fingerprint.py` — dHash (8×8, JPEG `draft` mode for fast decode) over all 2,636 files; union-find at Hamming ≤5 → stable `cluster_id` per scene. Emits `manifests/clusters.csv`.

`data/audit.py` — regenerates the contamination report as a committed artifact (`reports/data_audit.md`): cluster count, cross-split cluster count, holdout-with-train-twin count, label-conflict clusters, per-class scene counts, resolution histogram. This is evidence for the report and viva.

`data/split.py` — **group-aware stratified split keyed on `cluster_id`**, never on filename, seeded and deterministic. Target 70/15/15 by scene. Writes:
- `manifests/splits_clean.csv` — the real split
- `manifests/splits_original.csv` — the contaminated split, preserved verbatim so the comparison can be run

**Quarantine.** The 18 conflict clusters are routed to `data/review/` with a generated `review.html` showing each cluster's images side by side, current labels, and radio buttons for the correct one. Excluded from training until your agri supervisor rules. Re-importing a decided verdict is a single CLI command.

`data/cache.py` — resize longest side to 512px, JPEG q90, into `data/cache/`. Turns 3.5 GB into roughly 200 MB, small enough to upload to Colab once and cheap to load. Raw files untouched.

`data/dataset.py` — a `torch` `Dataset` driven **only by a manifest CSV**, never by directory walking. Directory structure can no longer determine a split.

**Regression test (`tests/test_split_integrity.py`):** asserts the intersection of `cluster_id` sets across train/val/test is empty, and that no manifest row points at a quarantined cluster. The bug found today can never silently return.

---

## Phase 2 — CNN classifier

**Backbone:** `timm` `efficientnet_b0`, ImageNet-pretrained — a genuine CNN as the spec describes, strong at this data scale, and small enough to export to mobile later. `mobilenetv3_large_100` trained as the deployment variant for size comparison.

**Input resolution: 384px.** Non-negotiable and worth defending in the report — Sigatoka's diagnostic signal is fine speckling and thin dark streaks that are simply gone at the conventional 224px. Train 384, evaluate 384.

**Augmentation, tuned to the domain:** `RandomResizedCrop(scale=0.5–1.0)`, horizontal/vertical flip, rotation, mild brightness/contrast, `RandAugment` (geometric ops only). **Hue jitter is deliberately excluded** — yellowing *is* the class signal for both diseases, and shifting hue destroys the label. Standard recipes get this wrong.

**Imbalance:** `WeightedRandomSampler` + label smoothing 0.05. **Primary metric is macro-F1 and per-class recall, with panama recall called out separately.** Accuracy is barred from the headline — at 4:1 imbalance it flatters a model that ignores panama entirely.

**Training:** AdamW, cosine schedule with warmup, early stop on val macro-F1, mixed precision, seeded. ~1,300 training scenes at 384px is roughly 10–20 min on a single GPU.

**Where training runs.** Training is driven from `notebooks/01_train_gpu.ipynb` on a **Google Cloud GPU instance**. The notebook is a thin driver, not a home for logic — it clones the repo, mounts/uploads `data/cache/` plus the manifests, and calls the same `banana_lifeline.vision.train` entry point the CLI uses. That keeps the notebook reviewable and stops training code from forking into an un-testable cell soup. Notebook outputs are stripped before commit; `runs/<timestamp>/` artifacts are what get pulled back down.

**5-fold group-aware cross-validation** on train+val, so results carry mean ± std instead of one lucky number. Test set touched once, at the end.

**The comparison table** — the core deliverable of the honesty decision. Identical recipe, two splits:

| Split | Accuracy | Macro-F1 | Panama recall |
|---|---|---|---|
| Original (contaminated) | expect ~97–99% | — | — |
| Clean (group-aware) | expect meaningfully lower | — | — |

**Shortcut check:** because every photo comes from one orchard on one day, the model may be reading background rather than leaf. Grad-CAM overlays for a stratified sample go into `reports/`, plus a control run on leaf-only center crops. If accuracy barely moves when background is removed, the model is genuinely reading the leaf.

**Calibration (`calibrate.py`):** temperature scaling fitted on val, then a risk–coverage curve to pick the abstain threshold τ against a target precision — instead of an arbitrary 0.7. Reports ECE before and after.

**Export:** ONNX + TFLite, with a parity test asserting exported and PyTorch logits agree within tolerance.

---

## Phase 3 — Out-of-distribution rejection

Farmers will photograph other crops, soil, faces, and blurry nothing. A three-class softmax always returns one of three diseases; without this phase the app confidently diagnoses a photo of a goat.

**Tier 1 — quality gate (cheap, runs first):** blur via variance-of-Laplacian, over/under-exposure, and a green-vegetation fraction check. Fails fast with an actionable message ("photo is blurry — hold steady and retake").

**Tier 2 — learned OOD:** Mahalanobis distance on penultimate features, with max-softmax-probability and energy score as baselines. Threshold calibrated against a negative set (other crops from PlantVillage plus a small curated non-plant set). Reported as **AUROC and FPR@95TPR**, so the claim is measured rather than asserted.

**Abstain policy (`vision/policy.py`)** — one place that decides among: confident answer · low-confidence answer with caveat · retake request · "consult an expert". Fully unit-tested, since this is the logic standing between a farmer and a wrong diagnosis.

---

## Phase 4 — RAG knowledge system

No corpus exists yet, so sourcing is part of the work.

**Sources** (`rag/sources.py` — a registry with URL, licence, retrieval date, authority tier): FAO banana/Fusarium TR4 guidance, CABI Compendium, Bioversity/ProMusa, PARC and provincial extension material, university extension publications. Licence recorded per document; anything unclear is excluded. Pakistan-specific material is tagged and ranked above generic international guidance where they disagree.

**Ingestion:** PDF/HTML → text with layout awareness, structure-aware chunking at ~500 tokens with overlap, preserving section headers as metadata. Payload per chunk: `source`, `url`, `section`, `disease`, `topic`, `language`, `authority_tier`.

**Embeddings: `BAAI/bge-m3`.** Chosen because the app must serve Urdu — an English-only embedder silently fails on Urdu queries, which would be discovered far too late. `bge-m3` is multilingual and emits dense *and* sparse vectors from one model.

**Qdrant:** named vectors (dense + sparse) in one collection, hybrid retrieval fused with Reciprocal Rank Fusion, then `bge-reranker-v2-m3` over the top ~20 to a final ~5. Docker locally, cloud-ready.

**Evaluation harness (`rag/eval.py`) — the part that makes this engineering rather than guesswork.** A golden set of 60–80 question/passage pairs in English and Urdu, covering all three diseases plus general farming, including questions the corpus *cannot* answer (to verify honest refusal). Measures Recall@k, MRR, nDCG. Every retrieval change is judged against it.

---

## Phase 5 — DeepSeek answer generation

**Grounding contract:** answers derive only from retrieved chunks; every claim carries a source; unsupported questions get an explicit "I don't have reliable information on this" rather than a fluent guess. Enforced by prompt *and* a post-generation check that flags unsourced claims.

**Structured output** matching the spec's fields — cause, symptoms, treatment and management, prevention, precautions — as a validated schema so the app renders consistently instead of parsing prose.

**Domain safety rules (hard-coded, not left to the model):**
- **Panama disease has no chemical cure.** Any generated fungicide treatment for panama is blocked outright. Guidance is containment: isolation, tool sterilisation, drainage, resistant cultivars, and not replanting susceptible varieties in infected soil.
- Agrochemical advice must come from retrieved, locally-approved sources — never generated dosages.
- Every chemical recommendation carries PPE and pre-harvest-interval warnings.
- Suspected TR4 escalates to official reporting guidance; it is a quarantine-grade pathogen, not a private problem.

**Panama guided follow-up (`generation/followup.py`)** — the confirmed design. When the model leans panama, instead of asserting, ask what a farmer can actually check: *are the older/lower leaves yellowing first and collapsing around the stem?* · *is the pseudostem splitting at the base?* · *cut the pseudostem — brown or reddish streaks inside?* Answers combine with the vision prior into a final confidence and a clear "confirm with an extension officer" when it stays ambiguous.

**Urdu:** generated directly, but backed by `generation/glossary.py` — a curated EN↔UR agricultural term list pinned in the prompt, because disease and chemical terminology is exactly where a general LLM drifts. Native-speaker spot-check of ~30 outputs before it is called done. Roman Urdu is deferred, with the glossary structured to make it a later addition.

**`pipeline.py`** ties it together: image → quality gate → OOD → classify → calibrate → abstain policy → retrieve → generate → (optional follow-up). One function the future FastAPI backend calls.

---

## Verification

Each phase is verifiable in isolation.

```bash
make audit      # regenerates reports/data_audit.md — confirms the 611/1033 finding
make split      # writes manifests; pytest asserts zero cluster overlap
pytest tests/test_split_integrity.py -v

# run on the Google Cloud GPU box, via notebooks/01_train_gpu.ipynb or directly:
make train CONFIG=configs/train.yaml SPLIT=clean
make train CONFIG=configs/train.yaml SPLIT=original   # the comparison run
make evaluate                                          # both tables + confusion matrices + Grad-CAM

make ood-eval   # AUROC / FPR@95TPR against the negative set
make index      # builds the Qdrant collection
make rag-eval   # Recall@k / MRR / nDCG on the golden set
```

**End-to-end smoke test:** run `pipeline.py` over a held-out farmer photo, a deliberately blurry photo, and a photo of a non-banana plant. Expected: a calibrated diagnosis with cited sources; a retake prompt; an OOD rejection. All three paths asserted in `tests/test_pipeline_e2e.py`.

**Definition of done:** honest metrics with error bars in `reports/model_card.md`, a dataset datasheet documenting the contamination and its fix, the two-split comparison table, the RAG golden-set scores, and a green CI run.

---

## Sequencing

| Phase | Gate before moving on |
|---|---|
| 0 Foundation | CI green |
| 1 Data audit + split | Split-integrity test passes; conflicts quarantined |
| 2 CNN | Both split results reported; Grad-CAM reviewed |
| 3 OOD | AUROC measured; abstain policy unit-tested |
| 4 RAG | Golden set built; Recall@k measured |
| 5 Generation | Safety rules tested; Urdu spot-checked |

Phase 1 blocks everything. Phase 4 can start in parallel with 2–3, since corpus sourcing is slow, human-paced work independent of the vision model.

---

## Open items (not blocking)

- **Agri supervisor sign-off** on the 18 quarantined clusters; panama/sigatoka confusion in the labels is the single biggest threat to the model's real-world accuracy.
- **DeepSeek API key** and **Qdrant** (local Docker vs cloud) needed before Phase 4–5 run.
- **Dataset breadth.** 287 panama scenes from one site on one day is thin, and it is the class that matters most. More sites, more dates, and pseudostem/whole-plant photos would help more than any modelling change. Worth flagging to your supervisor early — a second capture trip has a long lead time.
