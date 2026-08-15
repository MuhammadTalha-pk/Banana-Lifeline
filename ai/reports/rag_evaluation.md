# RAG Retrieval Evaluation

Golden set: **25 questions**.

| Metric | Value |
|---|---|
| Recall@1 | 0.85 |
| Recall@3 | 0.95 |
| Recall@5 | 1.00 |
| MRR | 0.904 |
| nDCG@5 | 0.932 |
| Refusal accuracy | 80% |

**Refusal accuracy** is how often the system correctly declined a question the
corpus cannot answer. A retrieval system that always returns its best guess scores
well on recall and is dangerous in agriculture, where the guess becomes a spray
recommendation someone acts on.

## By language

| Language | Recall@5 |
|---|---|
| en | 1.00 |
| ur | 1.00 |

Urdu questions are translated to English by DeepSeek before retrieval, so the
embedder only ever sees English. A gap here means the translation step is
losing detail -- check the logged original-vs-translated pair before blaming
retrieval.

