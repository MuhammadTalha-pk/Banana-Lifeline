# Banana Lifeline — RAG Knowledge Pipeline
PLAN.md`._

## Context

The vision model tells a farmer *what* the disease is. This layer tells them *what to do about
it* — grounded in authoritative agronomy rather than invented by a language model. Getting
this wrong is not a quality problem, it is a safety problem: a hallucinated fungicide dose or
a fabricated cure for an incurable disease reaches someone who will act on it.

**What actually exists right now.** `ai/Banana_Lifeline_RAG_Source_Pack/` holds 8 PDFs of
**2 KB each, 2 pages each**. They are placeholders. The pack's own README says so: *"The
original source documents are copyrighted/hosted by their respective organizations and are not
reproduced here."* Each stub names a URL. **There is no corpus yet** — but the source
selection is strong, which is the hard part.

All 8 URLs were checked and are live. Two need a browser user-agent (APS returns 403 and
TNAU times out against default curl; both return 200 with one). FAO's Fusarium manual is a
genuine 1.77 MB PDF; the rest are HTML, some behind a landing page.

**Confirmed decisions:** fetch the sources myself · BGE-M3 embeddings running locally ·
multilingual retrieval with Urdu answers (no translation hop) · the metadata schema below.

## The structural advantage worth building around

Generic RAG searches blind. **This system already knows the disease before it retrieves** —
the CNN just classified it. That turns the hardest part of retrieval into a metadata filter,
and it is why the schema below is load-bearing rather than decorative.

```json
{
  "source": "FAO",
  "disease": "panama",
  "topic": "prevention",
  "authority": "FAO/IPPC",
  "region": "global",
  "document_type": "technical_manual",
  "language": "en",
  "year": 2023
}
```

`region` earns its place for a specific reason: **none of the current sources are Pakistani.**
TNAU is Indian, FAO global, APS and Hawaii American. Pesticide registration is
jurisdiction-specific, so a product recommended in a Tamil Nadu extension page may be
unregistered — or banned — in Pakistan. Tagging region lets retrieval prefer local guidance
and lets generation add a "verify local registration" caveat when only foreign sources exist.

## Corpus scale, and why it disciplines the design

Once fetched, the corpus is roughly **300–500 pages**. The TNAU pages are 11–115 KB of HTML —
a few pages each. This is small, and that fact rules several fashionable techniques out.

| Technique | Verdict |
|---|---|
| Metadata pre-filtering | **Build.** Biggest precision win available, and free given the CNN. |
| Hybrid dense + sparse, RRF fused | **Build.** `TR4`, `Tridemorph`, dosages are exact-match terms BM25 nails and embeddings blur. |
| Cross-encoder reranking | **Build.** ~20 → 5. Cheap, reliably better. |
| Contextual chunk enrichment | **Build.** One-off DeepSeek pass at index time; fixes orphaned "the second application" chunks. |
| Small-to-big retrieval | **Build.** Match precise chunks, feed the surrounding section to the LLM. |
| Query rewriting (farmer → technical) | **Build.** Farmers write "leaves going yellow"; manuals say "progressive chlorosis". |
| GraphRAG / knowledge graph | **Skip.** 400 pages does not need entity graphs. Weeks of work, no measurable gain. |
| Fine-tuned embeddings | **Skip.** No labelled query/passage pairs to fine-tune on. |
| Agentic multi-hop retrieval | **Skip.** Adds seconds of latency for questions that are single-hop. |
| Embedding-similarity semantic chunking | **Skip.** These documents have real headings — use the structure that is already there. |

## Repository layout

```
ai/
  data/corpus/
    raw/            # fetched PDFs and HTML, never edited
    text/           # normalised plain text + per-document JSON metadata
    chunks.jsonl    # final chunks with full metadata
  src/banana_lifeline/rag/
    sources.py      # the 8-source registry: URL, licence, authority, region, year
    fetch.py        # polite downloader, browser UA, retries, landing-page resolution
    parse.py        # PDF and HTML -> clean text with structure preserved
    chunk.py        # heading-aware chunking + contextual enrichment
    classify.py     # assign disease / topic metadata per chunk
    embed.py        # BGE-M3 dense + sparse
    index.py        # Qdrant collection, named vectors, payload indexes
    retrieve.py     # filter -> hybrid -> RRF -> rerank -> expand
    eval.py         # golden set, Recall@k / MRR / nDCG
  configs/rag.yaml
  tests/test_rag.py
```

## Phases

### R0 — Acquisition and provenance

`sources.py` is a typed registry, one entry per document: URL, publisher, authority tier,
region, year, licence, retrieval date. `fetch.py` downloads with a browser user-agent, a
delay between requests, and retry-with-backoff; landing pages (IPPC, Hawaii, FAO Better
Farming) get a second hop to resolve the actual document link.

Every file lands in `data/corpus/raw/` with a sidecar JSON recording where it came from and
when. **Provenance is not optional** — an answer that cites a source must be able to name the
document, its publisher, and its retrieval date.

Licence terms are recorded per source. FAO and university extension material is generally
redistributable for non-commercial use; anything ambiguous is indexed for retrieval but
flagged so it is cited rather than quoted at length.

### R1 — Parsing and normalisation

PDFs via `pypdf` with layout awareness; HTML via `BeautifulSoup`, stripping navigation and
boilerplate. Output is plain text with headings preserved as markers, because the chunker
depends on them.

A quality gate rejects documents yielding suspiciously little text — that is the signature of
a scanned PDF needing OCR, and it should fail loudly rather than silently index nothing.

### R2 — Chunking and enrichment

Heading-aware splitting at ~500 tokens with ~80 token overlap, never breaking mid-sentence.
Section headings travel with the chunk.

**Contextual enrichment**: each chunk gets a one-line situating sentence prepended before
embedding — *"From FAO's Fusarium Wilt Manual, section 4.2 on soil management, discussing
quarantine measures after infection is confirmed."* A one-off DeepSeek pass over ~600 chunks,
a few cents in total. This is what stops an isolated paragraph about "the second application"
from being unretrievable.

`classify.py` assigns `disease` and `topic` per chunk — rule-based on headings and keywords
first, DeepSeek only for the ambiguous remainder, since deterministic rules are cheaper and
auditable. `topic` values: `symptoms`, `cause`, `treatment`, `prevention`, `precautions`,
`cultivation`, `general`.

### R3 — Embedding and indexing

**BGE-M3**, local on CPU. Chosen because it is genuinely multilingual — an Urdu question
matches English text directly, with no translation step where a mistranslated symptom could
retrieve the wrong disease — and because it emits dense *and* sparse vectors from one model,
so hybrid search needs no second system.

Expect ~30–45 min to index on your CPU, and ~1–2 s per query. Indexing is one-off; query
latency is the cost to watch, and is the reason a smaller fallback model stays configurable.

Qdrant: one collection, named vectors (`dense`, `sparse`), payload indexes on `disease`,
`topic`, and `region` so filtering is fast. Your Qdrant cluster is already connected and
empty.

### R4 — Retrieval

```
question + (disease from CNN)
   -> query rewrite            farmer vernacular -> technical vocabulary
   -> metadata pre-filter      disease + topic; region-preferred
   -> hybrid search            dense + sparse, top ~20 each
   -> RRF fusion
   -> cross-encoder rerank     bge-reranker-v2-m3, -> top 5
   -> context expansion        return each chunk's surrounding section
```

Filtering is *preferred*, not absolute: if a disease-filtered search returns too little, it
falls back to unfiltered rather than answering from nothing. General farming questions skip
the disease filter entirely.

### R5 — Evaluation

The part that separates engineering from guesswork. A golden set of **60–80 question/passage
pairs**, English and Urdu, covering all three diseases plus general cultivation — and
deliberately including questions the corpus **cannot** answer, to verify honest refusal.

Measured: Recall@k, MRR, nDCG, and refusal accuracy. Every retrieval change is judged against
it. I will draft the set from the corpus; the disease questions need your agri supervisor's
eye before they count as ground truth.

## Safety rules (hard-coded, not left to the model)

These are enforced in code and unit-tested, because a language model asked politely to be
careful is not a safety mechanism.

1. **Panama disease has no chemical cure.** Any generated fungicide treatment for panama is
   blocked. Guidance is containment only: isolation, tool sterilisation, drainage, resistant
   cultivars, not replanting susceptible varieties in infected soil.
2. **No generated dosages.** Chemical quantities must appear verbatim in a retrieved chunk or
   they are stripped. The model may quote; it may not calculate.
3. **Region caveat.** Advice drawn only from non-Pakistani sources carries an explicit
   "verify local registration" note.
4. **PPE and pre-harvest interval** accompany every chemical recommendation.
5. **Suspected TR4 escalates** to official reporting guidance — it is a quarantine-grade
   pathogen, not a private problem.
6. **Refuse when unsupported.** No retrieved support means "I don't have reliable information
   on this", never a fluent guess.

## Verification

```bash
banana rag fetch          # download all 8 sources, write provenance sidecars
banana rag build          # parse -> chunk -> enrich -> embed -> index
banana rag eval           # Recall@k / MRR / nDCG against the golden set
banana rag ask "meray kelay ke patton par peele dhabbe hain"   # end-to-end, Urdu
```

**Done when:** all 8 sources fetched with recorded provenance; every chunk carries the full
8-field metadata schema; golden-set scores recorded in `reports/rag_evaluation.md`; all six
safety rules covered by passing tests; and an Urdu question returns a grounded, cited answer.

## Sequencing

R0 → R1 → R2 → R3 → R4 → R5. R0 and R1 are independent of the vision model and can run while
CPU training finishes. R5's golden set is the gate before any retrieval tuning is trusted.

## Open items

- **Pakistani sources are absent.** Worth adding PARC and provincial extension material
  before this ships to real farmers; the `region` field is built to accommodate it.
- **Agri supervisor sign-off** on the golden set's disease questions.
- **Corpus is English-only.** Urdu retrieval works through multilingual embeddings, but
  answer quality in Urdu needs a native-speaker spot check of ~30 outputs.
