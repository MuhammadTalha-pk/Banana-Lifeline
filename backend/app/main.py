from __future__ import annotations

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import AuthUser, current_user
from .firestore_chat_service import (
    add_message,
    conversation_history,
    ensure_session,
)
from .generation_service import (
    GenerationNotReady,
    generate_answer,
    generate_diagnosis_guidance,
    is_generation_ready,
)
from .media_service import load_media, public_media_url, save_media
from .notification_service import create_diagnosis_notification
from .rag_service import RagNotReady, is_rag_ready, retrieve
from .scan_service import (
    assert_scan_owner,
    save_scan_diagnosis,
    save_scan_media,
    scan_context,
)
from .schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosisResponse,
    HealthResponse,
    TranscriptionResponse,
)
from .settings import get_settings
from .speech_service import SpeechNotReady, transcribe_wav
from .vision_service import (
    UnsupportedImageScope,
    VisionNotReady,
    is_vision_ready,
    predict_leaf,
)

settings = get_settings()
settings.media_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title='Banana Lifeline AI API',
    version='1.1.0',
    description=(
        'Firebase-authenticated AI/RAG API with zero-billing local media '
        'storage for Banana Lifeline.'
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=settings.cors_list != ['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# Zero-billing hackathon media host. Filenames are random UUIDs and directory
# listing is not exposed. For a public production deployment, replace this with
# private object storage or an authenticated/signed media delivery layer.
app.mount(
    '/media',
    StaticFiles(directory=str(settings.media_dir), check_dir=False),
    name='media',
)


def _diagnose_bytes(
    *,
    image_bytes: bytes,
    scan_target: str,
    language: str,
) -> DiagnosisResponse:
    try:
        result = predict_leaf(image_bytes, scan_target=scan_target)
    except UnsupportedImageScope as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VisionNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result.status == 'completed' and result.label != 'healthy':
        try:
            query = (
                'Panama disease Fusarium wilt TR4 banana symptoms '
                'containment prevention expert confirmation'
                if result.label == 'panama'
                else (
                    'Black Sigatoka black leaf streak banana symptoms '
                    'management prevention'
                )
            )
            chunks = retrieve(query)
            guidance = generate_diagnosis_guidance(
                label=result.display_name,
                language='ur' if language == 'ur' else 'en',
                chunks=chunks,
            )
            result.description = guidance['description']
            result.treatment = guidance['treatment']
            result.prevention = guidance['prevention']
            result.additional_advice = guidance['additional_advice']
            result.expert_recommended = (
                result.expert_recommended
                or guidance['expert_recommended']
            )
            result.sources = guidance['sources']
        except (RagNotReady, GenerationNotReady):
            # Keep the real model result. Never invent unavailable RAG guidance.
            pass

    return result


def _persist_diagnosis(
    *,
    uid: str,
    scan_id: str,
    language: str,
    result: DiagnosisResponse,
) -> None:
    try:
        save_scan_diagnosis(
            uid=uid,
            scan_id=scan_id,
            diagnosis=result,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if result.status == 'completed' and result.severity == 'high':
        create_diagnosis_notification(
            uid=uid,
            scan_id=scan_id,
            language='ur' if language == 'ur' else 'en',
            disease=result.display_name,
        )


def _location_dict(
    *,
    latitude: float | None,
    longitude: float | None,
    address: str | None,
    farm_name: str | None,
    plot_sector: str | None,
    row: str | None,
    plant_number: str | None,
) -> dict | None:
    if not any(
        [
            latitude is not None,
            longitude is not None,
            bool(address),
            bool(farm_name),
            bool(plot_sector),
            bool(row),
            bool(plant_number),
        ]
    ):
        return None

    return {
        'latitude': latitude,
        'longitude': longitude,
        'address': address,
        'farmName': farm_name,
        'plotSector': plot_sector,
        'row': row,
        'plantNumber': plant_number,
    }


def _chat_answer(
    *,
    user: AuthUser,
    session_id: str | None,
    message: str,
    language: str,
    related_scan_id: str | None,
    image_context: str | None,
    image_url: str | None,
    audio_url: str | None,
    latitude: float | None,
    longitude: float | None,
    address: str | None,
    farm_name: str | None,
    plot_sector: str | None,
    row: str | None,
    plant_number: str | None,
    note: str | None,
) -> ChatResponse:
    try:
        related_context = scan_context(
            uid=user.uid,
            scan_id=related_scan_id,
        )

        location_context = None
        location = _location_dict(
            latitude=latitude,
            longitude=longitude,
            address=address,
            farm_name=farm_name,
            plot_sector=plot_sector,
            row=row,
            plant_number=plant_number,
        )
        if location:
            location_context = (
                f"Farmer-shared location: latitude={latitude}, "
                f"longitude={longitude}, "
                f"address={address or 'not supplied'}, "
                f"farm={farm_name or 'not supplied'}, "
                f"plot/sector={plot_sector or 'not supplied'}, "
                f"row={row or 'not supplied'}, "
                f"plant={plant_number or 'not supplied'}"
            )

        note_context = f'Farmer image note: {note}' if note else None
        vision_context = '\n'.join(
            item
            for item in [
                related_context,
                image_context,
                location_context,
                note_context,
            ]
            if item
        ) or None

        sid = ensure_session(
            uid=user.uid,
            session_id=session_id,
            language=language,
            related_scan_id=related_scan_id,
            first_message=message,
        )

        history = conversation_history(
            uid=user.uid,
            session_id=sid,
            limit=12,
        )

        retrieval_query = '\n'.join(
            part
            for part in [
                message,
                note or '',
                image_context or '',
                related_context or '',
            ]
            if part
        )

        chunks = retrieve(retrieval_query)
        answer = generate_answer(
            question=message,
            language='ur' if language == 'ur' else 'en',
            chunks=chunks,
            history=history,
            vision_context=vision_context,
        )

        add_message(
            uid=user.uid,
            session_id=sid,
            sender='user',
            text=message,
            message_type=(
                'image'
                if image_url
                else ('audio' if audio_url else 'text')
            ),
            image_url=image_url,
            audio_url=audio_url,
            note=note,
            location=location,
        )

        message_id = add_message(
            uid=user.uid,
            session_id=sid,
            sender='assistant',
            text=answer.answer,
            sources=[source.model_dump() for source in answer.sources],
            ai_confidence=answer.confidence,
        )

        return ChatResponse(
            session_id=sid,
            message_id=message_id,
            answer=answer.answer,
            sources=answer.sources,
            confidence=answer.confidence,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RagNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GenerationNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(f'{settings.api_prefix}/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        vision_ready=is_vision_ready(),
        rag_ready=is_rag_ready(),
        generation_ready=is_generation_ready(),
        speech_enabled=settings.speech_enabled,
        details={
            'model_checkpoint': (
                str(settings.banana_model_checkpoint)
                if settings.banana_model_checkpoint
                else None
            ),
            'knowledge_dir': str(settings.knowledge_dir),
            'deepseek_model': (
                settings.deepseek_model
                if is_generation_ready()
                else None
            ),
            'vision_scope': 'banana leaf images only',
        },
    )


@app.post(
    f'{settings.api_prefix}/diagnose',
    response_model=DiagnosisResponse,
)
async def diagnose(
    request: Request,
    image: UploadFile = File(...),
    scan_id: str = Form(...),
    language: str = Form('en'),
    scan_target: str = Form('leaf'),
    note: str = Form(''),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    address: str = Form(''),
    user: AuthUser = Depends(current_user),
) -> DiagnosisResponse:
    del note, latitude, longitude, address

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail='Image is empty.')

    try:
        media_path, _ = save_media(
            uid=user.uid,
            kind='scans',
            content=image_bytes,
            original_name=image.filename,
            default_extension='.jpg',
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_url = public_media_url(
        str(request.base_url),
        media_path,
    )

    try:
        save_scan_media(
            uid=user.uid,
            scan_id=scan_id,
            image_url=media_url,
            media_path=media_path,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    result = _diagnose_bytes(
        image_bytes=image_bytes,
        scan_target=scan_target,
        language=language,
    )

    _persist_diagnosis(
        uid=user.uid,
        scan_id=scan_id,
        language=language,
        result=result,
    )
    return result


@app.post(
    f'{settings.api_prefix}/diagnose/retry/{{scan_id}}',
    response_model=DiagnosisResponse,
)
def retry_diagnosis(
    scan_id: str,
    user: AuthUser = Depends(current_user),
) -> DiagnosisResponse:
    try:
        scan = assert_scan_owner(uid=user.uid, scan_id=scan_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    media_path = str(scan.get('storagePath') or '').strip()
    if not media_path:
        raise HTTPException(
            status_code=422,
            detail='This scan has no locally stored image.',
        )

    try:
        image_bytes = load_media(media_path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=422,
            detail='The stored scan image is no longer available.',
        ) from exc

    language = str(scan.get('language') or 'en')
    result = _diagnose_bytes(
        image_bytes=image_bytes,
        scan_target='leaf',
        language=language,
    )

    _persist_diagnosis(
        uid=user.uid,
        scan_id=scan_id,
        language=language,
        result=result,
    )
    return result


@app.post(
    f'{settings.api_prefix}/chat',
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    user: AuthUser = Depends(current_user),
) -> ChatResponse:
    # Text-only endpoint. Legacy image/audio URLs are intentionally ignored in
    # zero-billing mode; media must use /chat/media as real multipart uploads.
    return _chat_answer(
        user=user,
        session_id=request.session_id,
        message=request.message,
        language=request.language,
        related_scan_id=request.related_scan_id,
        image_context=None,
        image_url=None,
        audio_url=None,
        latitude=request.latitude,
        longitude=request.longitude,
        address=request.address,
        farm_name=request.farm_name,
        plot_sector=request.plot_sector,
        row=request.row,
        plant_number=request.plant_number,
        note=request.note,
    )


@app.post(
    f'{settings.api_prefix}/chat/media',
    response_model=ChatResponse,
)
async def chat_media(
    request: Request,
    message: str = Form(...),
    language: str = Form('en'),
    session_id: str | None = Form(None),
    related_scan_id: str | None = Form(None),
    image: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    address: str | None = Form(None),
    farm_name: str | None = Form(None),
    plot_sector: str | None = Form(None),
    row: str | None = Form(None),
    plant_number: str | None = Form(None),
    note: str | None = Form(None),
    user: AuthUser = Depends(current_user),
) -> ChatResponse:
    image_url = None
    audio_url = None
    image_context = None

    if image is not None:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail='Chat image is empty.')

        media_path, _ = save_media(
            uid=user.uid,
            kind='chat-images',
            content=image_bytes,
            original_name=image.filename,
            default_extension='.jpg',
        )
        image_url = public_media_url(str(request.base_url), media_path)

        try:
            vision = predict_leaf(image_bytes, scan_target='leaf')
        except VisionNotReady as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    'The vision model is required for image chat but is '
                    f'not ready: {exc}'
                ),
            ) from exc
        except (UnsupportedImageScope, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        image_context = (
            f'Attached leaf screening: {vision.display_name}; '
            f'confidence={vision.confidence:.3f}; '
            f'severity={vision.severity}; '
            f"warning={vision.warning or 'none'}"
        )

    if audio is not None:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail='Voice note is empty.')

        media_path, _ = save_media(
            uid=user.uid,
            kind='chat-audio',
            content=audio_bytes,
            original_name=audio.filename,
            default_extension='.wav',
        )
        audio_url = public_media_url(str(request.base_url), media_path)

    return _chat_answer(
        user=user,
        session_id=session_id,
        message=message,
        language=language,
        related_scan_id=related_scan_id,
        image_context=image_context,
        image_url=image_url,
        audio_url=audio_url,
        latitude=latitude,
        longitude=longitude,
        address=address,
        farm_name=farm_name,
        plot_sector=plot_sector,
        row=row,
        plant_number=plant_number,
        note=note,
    )


@app.post(f'{settings.api_prefix}/profile/photo')
async def profile_photo(
    request: Request,
    image: UploadFile = File(...),
    user: AuthUser = Depends(current_user),
) -> dict[str, str]:
    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail='Profile image is empty.')

    relative_path, _ = save_media(
        uid=user.uid,
        kind='profile',
        content=content,
        original_name=image.filename,
        default_extension='.jpg',
    )
    return {
        'media_url': public_media_url(
            str(request.base_url),
            relative_path,
        ),
        'media_path': relative_path,
    }


@app.post(
    f'{settings.api_prefix}/transcribe',
    response_model=TranscriptionResponse,
)
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form('en'),
    user: AuthUser = Depends(current_user),
) -> TranscriptionResponse:
    del user

    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail='Audio is empty.')

    try:
        transcript = transcribe_wav(
            content,
            language='ur' if language == 'ur' else 'en',
        )
    except SpeechNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return TranscriptionResponse(
        transcript=transcript,
        language='ur' if language == 'ur' else 'en',
    )
