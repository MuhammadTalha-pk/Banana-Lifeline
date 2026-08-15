from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from google.cloud.firestore_v1 import Query

from .firebase_admin_service import db


def _now() -> datetime:
    return datetime.now(UTC)


def ensure_session(
    *,
    uid: str,
    session_id: str | None,
    language: str,
    related_scan_id: str | None,
    first_message: str,
) -> str:
    store = db()
    sid = session_id or str(uuid4())
    ref = store.collection('chat_sessions').document(sid)
    snap = ref.get()

    if snap.exists:
        data = snap.to_dict() or {}
        if data.get('ownerId') != uid:
            raise PermissionError('Chat session belongs to another user.')
        ref.set({'updatedAt': _now(), 'language': language}, merge=True)
        return sid

    title = first_message.strip().replace('\n', ' ')[:70] or 'Banana Expert chat'
    ref.set(
        {
            'ownerId': uid,
            'title': title,
            'language': language,
            'relatedScanId': related_scan_id,
            'createdAt': _now(),
            'updatedAt': _now(),
        }
    )
    return sid


def add_message(
    *,
    uid: str,
    session_id: str,
    sender: str,
    text: str,
    message_type: str = 'text',
    image_url: str | None = None,
    audio_url: str | None = None,
    note: str | None = None,
    location: dict | None = None,
    sources: list[dict] | None = None,
    ai_confidence: float | None = None,
) -> str:
    store = db()
    session_ref = store.collection('chat_sessions').document(session_id)
    session = session_ref.get()
    data = session.to_dict() or {}
    if not session.exists or data.get('ownerId') != uid:
        raise PermissionError('Invalid chat session.')

    message_id = str(uuid4())
    session_ref.collection('messages').document(message_id).set(
        {
            'ownerId': uid,
            'sender': sender,
            'text': text,
            'messageType': message_type,
            'imageUrl': image_url,
            'audioUrl': audio_url,
            'note': note,
            'location': location,
            'sources': sources or [],
            'aiConfidence': ai_confidence,
            'createdAt': _now(),
        }
    )
    session_ref.set({'updatedAt': _now()}, merge=True)
    return message_id


def conversation_history(*, uid: str, session_id: str, limit: int = 12) -> list[dict[str, str]]:
    store = db()
    session_ref = store.collection('chat_sessions').document(session_id)
    session = session_ref.get()
    data = session.to_dict() or {}
    if not session.exists or data.get('ownerId') != uid:
        raise PermissionError('Invalid chat session.')

    docs = list(
        session_ref.collection('messages')
        .order_by('createdAt', direction=Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    docs.reverse()
    result = []
    for snap in docs:
        item = snap.to_dict() or {}
        sender = item.get('sender')
        text = str(item.get('text') or '').strip()
        if sender == 'user' and text:
            result.append({'role': 'user', 'content': text})
        elif sender == 'assistant' and text:
            result.append({'role': 'assistant', 'content': text})
    return result
