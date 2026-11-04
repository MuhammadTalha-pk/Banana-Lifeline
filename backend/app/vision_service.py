from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
from PIL import Image

from .schemas import DiagnosisResponse
from .settings import get_settings


class VisionNotReady(RuntimeError):
    pass


class UnsupportedImageScope(ValueError):
    pass


@dataclass(slots=True)
class _Runtime:
    loaded: Any
    transform: Any
    torch: Any
    device: Any


def _add_friend_package_to_path(ai_root: Path) -> None:
    src = ai_root / 'src'
    if not src.is_dir():
        raise VisionNotReady(f'BANANA_AI_ROOT does not contain src/: {ai_root}')
    value = str(src.resolve())
    if value not in sys.path:
        sys.path.insert(0, value)


@lru_cache(maxsize=1)
def _runtime() -> _Runtime:
    settings = get_settings()
    if settings.banana_ai_root is None:
        raise VisionNotReady('BANANA_AI_ROOT is not configured.')
    if settings.banana_model_checkpoint is None:
        raise VisionNotReady('BANANA_MODEL_CHECKPOINT is not configured.')
    if not settings.banana_model_checkpoint.is_file():
        raise VisionNotReady(
            f'Model checkpoint does not exist: {settings.banana_model_checkpoint}'
        )

    _add_friend_package_to_path(settings.banana_ai_root)

    try:
        import torch
        from banana_lifeline.vision.model import load_checkpoint
        from banana_lifeline.vision.transforms import build_eval_transform
    except Exception as exc:
        raise VisionNotReady(
            'Friend AI vision dependencies are not installed. Install the AI package with [vision].'
        ) from exc

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    loaded = load_checkpoint(settings.banana_model_checkpoint, device=str(device))
    transform = build_eval_transform(loaded.train_config.image_size)
    return _Runtime(loaded=loaded, transform=transform, torch=torch, device=device)


def is_vision_ready() -> bool:
    settings = get_settings()
    return bool(
        settings.banana_ai_root
        and settings.banana_model_checkpoint
        and settings.banana_model_checkpoint.is_file()
    )


def _severity(label: str, confidence: float) -> str:
    if label == 'healthy':
        return 'low'
    if confidence >= 0.85:
        return 'high'
    if confidence >= 0.65:
        return 'medium'
    return 'unknown'


def predict_leaf(image_bytes: bytes, *, scan_target: str = 'leaf') -> DiagnosisResponse:
    if scan_target.lower().strip() not in {'leaf', 'banana_leaf'}:
        raise UnsupportedImageScope(
            'The supplied friend model is trained on banana leaf images only. '
            'Stem, fruit, corm, or whole-plant photos must not be classified by this checkpoint.'
        )

    runtime = _runtime()
    settings = get_settings()

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception as exc:
        raise ValueError('Uploaded file is not a readable image.') from exc

    arr = np.asarray(image)
    transformed = runtime.transform(image=arr)['image'].unsqueeze(0).to(runtime.device)

    with runtime.torch.no_grad():
        logits = runtime.loaded.model(transformed)
        logits = logits / max(runtime.loaded.temperature, 1e-6)
        probs = runtime.torch.softmax(logits, dim=1)[0].detach().cpu().numpy()

    index = int(np.argmax(probs))
    label = runtime.loaded.class_names[index]
    confidence = float(probs[index])

    if confidence < settings.vision_min_confidence:
        return DiagnosisResponse(
            request_id=str(uuid4()),
            status='abstained',
            label='uncertain',
            display_name='Uncertain result',
            confidence=confidence,
            severity='unknown',
            expert_recommended=True,
            warning=(
                'The model confidence is below the configured threshold. '
                'Retake a clear leaf photo or consult an agriculture expert.'
            ),
        )

    display = {
        'healthy': 'Healthy leaf pattern',
        'panama': 'Suspected Panama disease / Fusarium wilt',
        'sigatoka': 'Suspected Black Sigatoka / black leaf streak',
    }.get(label, label)

    warning = None
    expert = label == 'panama'
    if label == 'panama':
        warning = (
            'This is a screening result from a leaf-photo model, not a confirmed TR4 diagnosis. '
            'The supplied AI project explicitly requires confirming whole-plant/pseudostem signs '
            'and expert or laboratory review before asserting Panama disease.'
        )

    return DiagnosisResponse(
        request_id=str(uuid4()),
        status='completed',
        label=label,
        display_name=display,
        confidence=confidence,
        severity=_severity(label, confidence),
        expert_recommended=expert,
        warning=warning,
    )
