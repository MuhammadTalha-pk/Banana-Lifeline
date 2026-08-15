# Banana Lifeline — decisions and constraints

Read this before changing anything under `ai/`. It records **why** things are the way they
are, so a later change does not quietly undo a fix. Code structure, file lists, and history
live in the repo and in git; they are not repeated here.

Scope so far: the **AI layer only**. Flutter app, FastAPI service, and Firebase are out of
scope by the user's instruction.

---

## Standing instructions

- **Report the honest number, not the flattering one.** Every metric in `ai/reports/` must be
  reproducible from a committed artifact. If a number improves, check whether the measurement
  changed before believing it.
- **Re-measure after changing anything upstream of a threshold.** A tuned constant is only
  valid for the pipeline it was tuned on. This has bitten us twice; see the log below.
- **Safety belongs in code, never in a prompt.** A model asked politely to be careful is not
  a safety mechanism.
- The project's distribution name is `banana-lifeline`; the import name is `banana_lifeline`.
  Hyphen for the package, underscore for the module. This is standard, not a typo.
- Everything runs from `ai/.venv` on Python 3.11. Anaconda and system Python do not have the
  package installed, and 3.13 lacks wheels for parts of the training stack.

---

## Architecture decisions

### Vision

**Splits are keyed on scene, never on filename.** The raw dataset was 59% contaminated —
611 of 1,033 holdout images had a near-twin in train — and MD5 reported it clean because the
duplicates had been re-encoded. Perceptual hashing plus union-find clustering is what finds
them. `tests/test_split_integrity.py` fails if any scene spans two splits; do not weaken it.

**Both split results are reported.** Contaminated 0.833 macro-F1 vs honest 0.765. The gap is
the finding, not an embarrassment.

**Macro-F1 and per-class recall, never accuracy as the headline.** Sigatoka outnumbers Panama
about 4:1.

**Hue jitter raises `ValueError` in `transforms.py`.** Leaf yellowing *is* the class signal,
so shifting hue produces mislabelled training images. This is blocked rather than omitted
because standard augmentation recipes include it.

**384 px input, not 224.** Sigatoka's diagnostic signal is fine speckling and thin streaks and
it disappears at 224.

**Panama is never asserted from a leaf photo.** Its diagnostic signs are whole-plant collapse
and brown vascular tissue in a cut pseudostem. A Panama prediction triggers four questions a
farmer can actually check. An expert reviewer ruled 16 of 18 contested images undecidable from
the leaf alone, and the confusion matrix still shows 30 Sigatoka leaves called Panama.

**The Mahalanobis OOD detector was built, measured, and deleted.** It rejected 100% of unseen
real leaves and scored flat grey as more normal than a genuine photo, at every PCA dimension
tried. Only the tier-1 quality gate runs. Reviving it needs a real negative set, not more
tuning — `vision/ood.py` documents the measurement so nobody rebuilds it blind.

### Retrieval and generation

**Translate-before-retrieve.** Urdu → English → retrieve → generate English → enforce safety
→ translate out. The corpus and the embedder are English, and this lets us use the strongest
English retriever rather than paying a multilingual quality tax.

**Answers are generated in English and translated afterwards — this is a safety requirement.**
The safety rules are English regexes. Generating straight into Urdu passed every check while
quoting a spray rate with no protective-equipment warning, because none of the patterns
matched. A safety layer that silently does nothing for half the users is worse than none.

**Embedder capability comes from the model name, never from which import succeeded.**
`FlagEmbedding.BGEM3FlagModel` accepts any HF model and wraps it as an `M3Embedder` without
checking, which made `all-mpnet` claim sparse vectors non-deterministically.

**Retrieval asks the collection what vectors it declares** rather than trusting the embedder
to describe itself. A mismatch is a 400 on every query.

**Refusal is a valid answer**, and it happens before a token is spent when retrieval is weak.

**Answerability is a routing decision, not a retrieval score.** See the log entry below —
this is the most recent and most easily-undone decision here.

### Models load once per process

`rag.embed.get_embedder`, `rag.index._client`, `rag.retrieve._load_reranker`,
`rag.retrieve._collection_has_sparse`, and `vision.model.load_cached_checkpoint` are all
process-cached, and `pipeline.warm_up()` loads them up front without touching any API.

`vision.model.load_checkpoint` stays **uncached** on purpose: training and evaluation need a
fresh model they may mutate. Only inference uses the cached one.

---

## Decision log — things that were changed after being measured

Each of these looked correct until something was measured. They are the entries most likely
to be re-broken.

| Decision | Why, and what it replaced |
|---|---|
| **Refusal moved from the retrieval threshold to the intent router** | The cross-encoder score cannot separate the two populations: answerable questions span −4.9 to +7.5, unanswerable −8.0 to −1.3. At −3.5 it refused "I have panama disease in my farm, what should I do" (−4.47) while answering "what fertiliser dose for my wheat crop" (−1.53). "Does this passage answer this question?" and "is this question about bananas?" are different questions. The threshold is now a −6.0 backstop. |
| **`add_crop_context` never expands a question naming another subject** | Appending "(banana cultivation)" to a wheat question made it retrieve banana passages and score as answerable. The helper was added to stop vague *banana* questions being refused and it silently halved refusal accuracy, because the threshold was never re-measured afterwards. |
| **`looks_technical` returns False when another crop, animal, or market topic is named** | A keyword scan cannot tell "fertiliser for my wheat" from "fertiliser for my bananas". Those go to the model. |
| **Meta-questions route to the greeting reply** | The model classified "can you help me" as out_of_scope, so a farmer opening with it was told "I only know about bananas — I cannot help with that." |
| **Intent routing is asymmetric: every uncertain case resolves to `technical`** | Misrouting a real question means a farmer with a dying crop is told "hello". Misrouting a greeting costs one wasted search. |
| **`disease` in the Streamlit app is owned by the uploader** | Nothing but the Clear button ever reset it, so replies claimed a photo that was never sent. |
| **DeepSeek `max_tokens` is 6000, and truncation is a failure** | Reasoning tokens count against the budget without appearing in the content. At 900, English truncated mid-sentence and Urdu returned an empty string — indistinguishable from a refusal. |
| **Models downloaded with `snapshot_download(allow_patterns=…)`** | `sentence-transformers` pulls the whole repo, 28 files including ONNX, OpenVINO and TensorFlow weights. This caused three indexing stalls. |
| **Startup guards `raise SystemExit(1)`** | `st.stop()` is a no-op in Streamlit's bare mode, so `python app.py` fell through to an unrelated `NameError`. |
| **Calibration is stored in the checkpoint** | A checkpoint shipped with `temperature: 1.0` while the report quoted 2.582, so the confidence threshold meant nothing. |
| **Verdict import recomputes the contested set from fingerprints** | It used to validate against a manifest that shrank on each import, so re-importing failed. |

---

## Open items

- **Agronomist sign-off** on the 18 quarantined label-conflict clusters, and on the golden
  set's disease questions. Until then the golden set encodes a reading of the corpus, not
  domain authority.
- **No Pakistani sources in the corpus.** All eight are FAO, Indian, or American. Pesticide
  registration is jurisdiction-specific; the `region` field and preference logic are built and
  waiting for PARC or provincial material.
- **Corpus contains some navigation boilerplate.** A TNAU chunk beginning "Home | About Us |
  Success Stories" ranked first for a real query. `rag/parse.py` needs a boilerplate filter.
- **Refusal accuracy needs re-measuring** and `ai/reports/rag_evaluation.md` regenerating after
  the routing change; the recorded 80% predates it.
- **Dataset breadth.** 287 Panama scenes, one site, one day, leaves only. It is the class that
  matters most and the thinnest one.
- **Urdu spot-check** of ~30 generated answers by a native speaker.

---

## Secrets

`ai/.env` holds `DEEPSEEK_API_KEY`, `QDRANT_API_KEY`, and `QDRANT_URL`. It is gitignored, with
`tests/test_secrets.py::test_env_file_is_gitignored` as the regression guard. Never print key
values — presence and character counts only. Model checkpoints (`*.pt`) are also gitignored.
