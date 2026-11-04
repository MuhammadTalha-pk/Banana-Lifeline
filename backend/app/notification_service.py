from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from firebase_admin import messaging

from .firebase_admin_service import db


def _now() -> datetime:
    return datetime.now(UTC)


def create_diagnosis_notification(*, uid: str, scan_id: str, language: str, disease: str) -> None:
    if language == 'ur':
        title = 'اہم بیماری کی اطلاع'
        body = f'{disease} کا شدید اسکریننگ نتیجہ ملا ہے۔ رپورٹ اور احتیاطی اقدامات دیکھیں۔'
    else:
        title = 'Important disease warning'
        body = f'A high-risk screening result was returned for {disease}. Review the report and precautions.'

    store = db()
    notification_id = str(uuid4())
    store.collection('notifications').document(notification_id).set(
        {
            'ownerId': uid,
            'scanId': scan_id,
            'title': title,
            'body': body,
            'read': False,
            'type': 'high_risk_diagnosis',
            'createdAt': _now(),
        }
    )

    user = store.collection('users').document(uid).get().to_dict() or {}
    tokens = [str(t) for t in (user.get('fcmTokens') or []) if str(t).strip()]
    if not tokens:
        return

    messages = [
        messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={'type': 'high_risk_diagnosis', 'scan_id': scan_id},
            token=token,
        )
        for token in tokens[:500]
    ]
    try:
        messaging.send_each(messages)
    except Exception:
        # The Firestore notification is already persisted. FCM delivery failures
        # should never make a completed diagnosis endpoint fail.
        pass
