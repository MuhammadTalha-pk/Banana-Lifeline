"""Retrieval evaluation.

Without this, tuning retrieval is guesswork dressed up as engineering — every change *feels*
like an improvement when you try three queries by hand.

The golden set deliberately includes questions the corpus **cannot** answer. Measuring only
successful retrieval optimises for a system that always returns something, which is exactly
the failure mode that makes RAG dangerous in agriculture: a confident fungicide
recommendation assembled from passages that were merely the least-bad matches.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from banana_lifeline.config import Paths


@dataclass(slots=True)
class GoldenQuestion:
    """One evaluation case."""

    question: str
    language: str
    disease: str | None
    topic: str | None

    #: Substrings that must appear in a correct passage. Kept as text rather than chunk ids
    #: so the golden set survives re-chunking, which would otherwise invalidate it entirely.
    expect_terms: list[str] = field(default_factory=list)

    #: Source slugs that could legitimately answer this.
    expect_sources: list[str] = field(default_factory=list)

    #: True when the corpus genuinely cannot answer and refusal is the correct behaviour.
    unanswerable: bool = False
    note: str = ""


@dataclass(slots=True)
class QuestionResult:
    question: str
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float
    ndcg: float
    correctly_refused: bool | None
    top_source: str
    top_score: float


@dataclass(slots=True)
class EvaluationReport:
    n_questions: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    ndcg: float
    refusal_accuracy: float | None
    per_language: dict[str, float]
    results: list[QuestionResult]

    def summary(self) -> str:
        refusal = (
            f"refusal {self.refusal_accuracy:.0%}" if self.refusal_accuracy is not None else "—"
        )
        return (
            f"R@1 {self.recall_at_1:.2f}  R@3 {self.recall_at_3:.2f}  R@5 {self.recall_at_5:.2f}  "
            f"MRR {self.mrr:.3f}  nDCG {self.ndcg:.3f}  {refusal}"
        )


def _passage_matches(text: str, terms: list[str]) -> bool:
    """A passage counts as relevant when it contains any expected term.

    Any, not all: a correct passage about chemical control need not repeat the disease name
    that the section heading already established.
    """
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _ndcg(relevances: list[int], k: int = 5) -> float:
    gains = [rel / math.log2(position + 2) for position, rel in enumerate(relevances[:k])]
    ideal = [1 / math.log2(position + 2) for position in range(min(sum(relevances), k))]
    return sum(gains) / sum(ideal) if ideal else 0.0


def evaluate_retrieval(
    questions: list[GoldenQuestion],
    retriever: Any,
    *,
    top_k: int = 5,
) -> EvaluationReport:
    """Run the golden set through a retriever.

    ``retriever`` is any callable taking ``(question, disease, topic)`` and returning a
    ``RetrievalResult`` — injected rather than imported so the harness can be tested
    without a live Qdrant.
    """
    results: list[QuestionResult] = []
    refusal_correct = 0
    refusal_total = 0
    language_hits: dict[str, list[float]] = {}

    for question in questions:
        outcome = retriever(question.question, question.disease, question.topic)
        passages = outcome.passages[:top_k]

        if question.unanswerable:
            refusal_total += 1
            # Correct behaviour is a weak result: nothing found, or nothing convincing.
            refused = outcome.is_weak
            refusal_correct += int(refused)
            results.append(
                QuestionResult(
                    question=question.question,
                    hit_at_1=False,
                    hit_at_3=False,
                    hit_at_5=False,
                    reciprocal_rank=0.0,
                    ndcg=0.0,
                    correctly_refused=refused,
                    top_source=passages[0].source if passages else "",
                    top_score=outcome.best_score,
                )
            )
            continue

        expected_sources = set(question.expect_sources)
        relevances = [
            int(
                _passage_matches(p.text, question.expect_terms)
                or p.chunk_id.split("__")[0] in expected_sources
            )
            for p in passages
        ]

        first = next((i for i, rel in enumerate(relevances) if rel), None)
        reciprocal = 1.0 / (first + 1) if first is not None else 0.0

        result = QuestionResult(
            question=question.question,
            hit_at_1=bool(relevances[:1] and relevances[0]),
            hit_at_3=any(relevances[:3]),
            hit_at_5=any(relevances[:5]),
            reciprocal_rank=reciprocal,
            ndcg=_ndcg(relevances, top_k),
            correctly_refused=None,
            top_source=passages[0].source if passages else "",
            top_score=outcome.best_score,
        )
        results.append(result)
        language_hits.setdefault(question.language, []).append(float(result.hit_at_5))

    answerable = [r for r in results if r.correctly_refused is None]
    n = max(len(answerable), 1)

    return EvaluationReport(
        n_questions=len(questions),
        recall_at_1=sum(r.hit_at_1 for r in answerable) / n,
        recall_at_3=sum(r.hit_at_3 for r in answerable) / n,
        recall_at_5=sum(r.hit_at_5 for r in answerable) / n,
        mrr=sum(r.reciprocal_rank for r in answerable) / n,
        ndcg=sum(r.ndcg for r in answerable) / n,
        refusal_accuracy=(refusal_correct / refusal_total) if refusal_total else None,
        per_language={lang: sum(hits) / len(hits) for lang, hits in language_hits.items() if hits},
        results=results,
    )


def load_golden_set(path: Path) -> list[GoldenQuestion]:
    if not path.is_file():
        raise FileNotFoundError(f"No golden set at {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    return [GoldenQuestion(**entry) for entry in payload]


def write_golden_set(questions: list[GoldenQuestion], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(q) for q in questions], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path


def render_report(report: EvaluationReport) -> str:
    lines = [
        "# RAG Retrieval Evaluation",
        "",
        f"Golden set: **{report.n_questions} questions**.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Recall@1 | {report.recall_at_1:.2f} |",
        f"| Recall@3 | {report.recall_at_3:.2f} |",
        f"| Recall@5 | {report.recall_at_5:.2f} |",
        f"| MRR | {report.mrr:.3f} |",
        f"| nDCG@5 | {report.ndcg:.3f} |",
    ]

    if report.refusal_accuracy is not None:
        lines.append(f"| Refusal accuracy | {report.refusal_accuracy:.0%} |")

    lines += [
        "",
        "**Refusal accuracy** is how often the system correctly declined a question the",
        "corpus cannot answer. A retrieval system that always returns its best guess scores",
        "well on recall and is dangerous in agriculture, where the guess becomes a spray",
        "recommendation someone acts on.",
        "",
    ]

    if report.per_language:
        lines += ["## By language", "", "| Language | Recall@5 |", "|---|---|"]
        lines += [
            f"| {lang} | {value:.2f} |" for lang, value in sorted(report.per_language.items())
        ]
        lines += [
            "",
            "Urdu questions are translated to English by DeepSeek before retrieval, so the",
            "embedder only ever sees English. A gap here means the translation step is",
            "losing detail -- check the logged original-vs-translated pair before blaming",
            "retrieval.",
            "",
        ]

    failures = [r for r in report.results if r.correctly_refused is None and not r.hit_at_5]
    if failures:
        lines += ["## Misses", "", "| Question | Top source | Score |", "|---|---|---|"]
        lines += [
            f"| {r.question[:70]} | {r.top_source or '—'} | {r.top_score:.3f} |" for r in failures
        ]

    return "\n".join(lines) + "\n"


def write_report(report: EvaluationReport, paths: Paths) -> Path:
    paths.reports.mkdir(parents=True, exist_ok=True)
    destination = paths.reports / "rag_evaluation.md"
    destination.write_text(render_report(report), encoding="utf-8")
    (paths.reports / "rag_evaluation.json").write_text(
        json.dumps(
            {
                "recall_at_1": report.recall_at_1,
                "recall_at_3": report.recall_at_3,
                "recall_at_5": report.recall_at_5,
                "mrr": report.mrr,
                "ndcg": report.ndcg,
                "refusal_accuracy": report.refusal_accuracy,
                "per_language": report.per_language,
                "n_questions": report.n_questions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination
