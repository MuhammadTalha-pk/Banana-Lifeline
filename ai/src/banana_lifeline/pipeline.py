"""The public entry point: a photo and a question in, grounded guidance out.

This is the one function a FastAPI backend needs to call. The ordering is the safety
argument of the whole system, cheapest and most certain checks first:

    photo -> quality gate -> OOD -> classify -> calibrate -> policy
                                                              |
                    (retake / refer to expert / follow-up) <--+
                                                              |
       question -> route -> translate -> retrieve -> generate -+
                     |                                         |
   (greeting / out of scope)                         safety rules

Nothing downstream runs if an earlier stage says stop. A blurry photo never reaches the
classifier; a goat never reaches retrieval; "hi" never reaches the knowledge base; a weak
retrieval never reaches generation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from banana_lifeline.config import CLASS_NAMES, Paths, get_paths
from banana_lifeline.vision.ood import QualityReport, assess_quality
from banana_lifeline.vision.policy import Action, decide


@dataclass(slots=True)
class PipelineResult:
    """Everything the app needs to render, and everything an auditor needs to explain it."""

    action: str
    message: str
    disease: str | None = None
    confidence: float = 0.0
    answer: str = ""
    citations: list[dict[str, str]] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    safety_violations: list[str] = field(default_factory=list)

    # audit trail
    reason: str = ""
    quality: dict[str, float] = field(default_factory=dict)
    retrieval_similarity: float = 0.0
    translated_query: str | None = None

    #: How the message was routed: greeting, technical, or out_of_scope. Empty for photo
    #: diagnoses, which are never routed.
    intent: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _classify(image_path: Path, checkpoint: Path, paths: Paths) -> tuple[str | None, float, Any]:
    """Run the calibrated classifier. Returns ``(disease, confidence, features)``."""
    import numpy as np
    import torch
    from PIL import Image

    from banana_lifeline.vision.calibrate import softmax
    from banana_lifeline.vision.model import extract_features, load_cached_checkpoint
    from banana_lifeline.vision.transforms import build_eval_transform

    loaded = load_cached_checkpoint(checkpoint)
    transform = build_eval_transform(loaded.train_config.image_size)

    with Image.open(image_path) as handle:
        array = np.asarray(handle.convert("RGB"))

    tensor = transform(image=array)["image"].unsqueeze(0)

    with torch.no_grad():
        logits = loaded.model(tensor).float().cpu().numpy()
        features = extract_features(loaded.model, tensor).float().cpu().numpy()

    # The stored temperature is what makes the confidence threshold mean anything. A
    # checkpoint that shipped uncalibrated would silently return overconfident scores.
    probabilities = softmax(logits, loaded.temperature)[0]
    index = int(probabilities.argmax())

    return CLASS_NAMES[index], float(probabilities[index]), features


@lru_cache(maxsize=4)
def _load_detector(checkpoint: Path) -> Any:
    """Load a fitted OOD detector beside the checkpoint, if one exists.

    None is the normal state right now: the Mahalanobis detector measured worse than useless
    on this model (see ``vision/ood.py``), so no detector file is shipped and only the tier-1
    quality gate runs. The hook stays so a validated detector can be dropped in later.
    """
    import json

    path = checkpoint.parent / "ood_detector.json"
    if not path.is_file():
        return None

    from banana_lifeline.vision.ood import MahalanobisDetector

    return MahalanobisDetector.from_dict(json.loads(path.read_text(encoding="utf-8")))


def diagnose(
    image_path: str | Path,
    question: str = "",
    *,
    checkpoint: Path | None = None,
    language: str = "en",
    paths: Paths | None = None,
    detector: Any = None,
    generate: bool = True,
) -> PipelineResult:
    """Diagnose a photo and answer a question about it."""
    resolved_paths = paths or get_paths()
    image = Path(image_path)
    checkpoint_path = checkpoint or (resolved_paths.runs / "cpu_clean" / "best.pt")

    # --- 1. Is the photo usable at all? ------------------------------------------------
    quality: QualityReport = assess_quality(image)
    quality_payload = {
        "blur": quality.blur_score,
        "brightness": quality.brightness,
        "vegetation": quality.vegetation_fraction,
    }

    if not quality.passed:
        decision = decide(quality=quality, disease=None, confidence=0.0)
        return PipelineResult(
            action=decision.action.value,
            message=decision.message,
            reason=decision.reason,
            quality=quality_payload,
        )

    # --- 2. Classify, and check it is a banana leaf at all ------------------------------
    disease, confidence, features = _classify(image, checkpoint_path, resolved_paths)

    active_detector = detector if detector is not None else _load_detector(checkpoint_path)
    is_ood = bool(active_detector.is_ood(features)[0]) if active_detector is not None else False

    decision = decide(quality=quality, disease=disease, confidence=confidence, is_ood=is_ood)

    result = PipelineResult(
        action=decision.action.value,
        message=decision.message,
        disease=decision.disease,
        confidence=decision.confidence,
        follow_up_questions=decision.follow_up_questions,
        reason=decision.reason,
        quality=quality_payload,
    )

    if not decision.should_retrieve or not generate:
        return result

    # --- 3. Retrieve guidance, then rewrite it -----------------------------------------
    from banana_lifeline.generation.answer import generate_answer
    from banana_lifeline.rag.retrieve import retrieve

    # A photo carries its own question, so small talk sent alongside one is not a reason to
    # withhold the diagnosis -- it is a reason to answer the question the photo asked.
    asked = question if question and _is_technical(question) else ""
    asked = asked or _default_question(decision.disease, language)
    retrieved = retrieve(asked, disease=decision.disease, top_k=5)

    result.retrieval_similarity = retrieved.top_similarity
    result.translated_query = retrieved.rewritten_query

    answer = generate_answer(
        asked,
        retrieved,
        disease=decision.disease,
        language=language,
    )

    result.answer = answer.text
    result.citations = answer.citations
    result.safety_violations = answer.safety_violations
    return result


def ask(
    question: str,
    *,
    disease: str | None = None,
    language: str = "en",
    route: bool = True,
) -> PipelineResult:
    """Answer a text-only question, with no photo.

    The chatbot must work without an image -- planting, soil, irrigation, harvesting.

    Messages are routed before retrieval runs. "hi" is not a query, and searching an agronomy
    corpus for it returns five passages that are merely about bananas, which the model then
    turns into a confident essay on something nobody asked about. Only technical messages
    reach the knowledge base; ``route=False`` restores the old unconditional behaviour for
    evaluation runs, where every input is a question by construction.
    """
    from banana_lifeline.generation.answer import generate_answer
    from banana_lifeline.generation.intent import (
        Intent,
        classify,
        greeting_text,
        out_of_scope_text,
    )
    from banana_lifeline.rag.retrieve import retrieve

    routing = classify(question) if route else None

    if routing is not None and routing.intent is not Intent.TECHNICAL:
        conversational = routing.intent is Intent.GREETING
        return PipelineResult(
            action=(Action.GREETING if conversational else Action.OUT_OF_SCOPE).value,
            message="",
            disease=disease,
            answer=(
                greeting_text(language, disease) if conversational else out_of_scope_text(language)
            ),
            reason=routing.reason,
            intent=routing.intent.value,
        )

    retrieved = retrieve(question, disease=disease, top_k=5)
    answer = generate_answer(question, retrieved, disease=disease, language=language)

    return PipelineResult(
        action=Action.ANSWER.value if not answer.refused else Action.REFER_TO_EXPERT.value,
        message="",
        disease=disease,
        answer=answer.text,
        citations=answer.citations,
        safety_violations=answer.safety_violations,
        retrieval_similarity=retrieved.top_similarity,
        translated_query=retrieved.rewritten_query,
        reason="text-only question",
        intent=Intent.TECHNICAL.value if routing is not None else "",
    )


def warm_up(*, checkpoint: Path | None = None, paths: Paths | None = None) -> None:
    """Load every model this process needs, before a user is waiting on one.

    All three loaders cache for the life of the process, so this is purely about *when* the
    cost is paid. Call it at server start; the first question then costs a forward pass
    instead of several hundred megabytes of disk reads.

    Deliberately touches no API. The apps used to warm up by asking a real question, which
    spent a DeepSeek call on every restart to load models that a plain import could load.

    Missing artifacts are not an error here: the RAG half is useful on a machine that has no
    trained checkpoint, and warm-up must not be the thing that decides otherwise.
    """
    from banana_lifeline.rag.embed import get_embedder
    from banana_lifeline.rag.retrieve import _load_reranker

    get_embedder()
    _load_reranker()

    resolved = paths or get_paths()
    checkpoint_path = checkpoint or (resolved.runs / "cpu_clean" / "best.pt")
    if checkpoint_path.is_file():
        from banana_lifeline.vision.model import load_cached_checkpoint

        load_cached_checkpoint(checkpoint_path)


def _is_technical(question: str) -> bool:
    from banana_lifeline.generation.intent import Intent, classify

    return classify(question).intent is Intent.TECHNICAL


def _default_question(disease: str | None, language: str) -> str:
    if disease == "healthy":
        return "How do I keep my banana plants healthy and prevent disease?"
    if disease:
        return f"What is {disease}, what causes it, and what should I do about it?"
    return "What should I do about my banana plants?"
