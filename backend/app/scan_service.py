from __future__ import annotations

from datetime import UTC, datetime

from .firebase_admin_service import db
from .schemas import DiagnosisResponse


def _now() -> datetime:
    return datetime.now(UTC)


def assert_scan_owner(*, uid: str, scan_id: str) -> dict:
    snap = db().collection('plant_scans').document(scan_id).get()
    data = snap.to_dict() or {}
    if not snap.exists or data.get('ownerId') != uid:
        raise PermissionError('Invalid scan id for this user.')
    return data


def save_scan_media(
    *,
    uid: str,
    scan_id: str,
    image_url: str,
    media_path: str,
) -> None:
    assert_scan_owner(uid=uid, scan_id=scan_id)
    db().collection('plant_scans').document(scan_id).set(
        {
            'imageUrl': image_url,
            # Keep the existing model field name for Flutter compatibility.
            'storagePath': media_path,
            'updatedAt': _now(),
        },
        merge=True,
    )


def save_scan_diagnosis(
    *,
    uid: str,
    scan_id: str,
    diagnosis: DiagnosisResponse,
) -> None:
    assert_scan_owner(uid=uid, scan_id=scan_id)
    db().collection('plant_scans').document(scan_id).set(
        {
            'status': (
                'completed'
                if diagnosis.status == 'completed'
                else 'needs_review'
            ),
            'diagnosis': diagnosis.model_dump(mode='json'),
            'updatedAt': _now(),
        },
        merge=True,
    )


def scan_context(*, uid: str, scan_id: str | None) -> str | None:
    if not scan_id:
        return None

    data = assert_scan_owner(uid=uid, scan_id=scan_id)
    diagnosis = data.get('diagnosis') or {}
    location = data.get('location') or {}

    parts = [
        f'Related scan id: {scan_id}',
        'Screening label: '
        + str(
            diagnosis.get('displayName')
            or diagnosis.get('display_name')
            or diagnosis.get('label')
            or 'not available'
        ),
        'Confidence: '
        + str(
            diagnosis.get('confidence')
            if diagnosis.get('confidence') is not None
            else 'not available'
        ),
        f"Severity: {diagnosis.get('severity') or 'not available'}",
        f"Farmer note: {data.get('note') or 'none'}",
        (
            'Farm place: '
            f"{location.get('farmName') or ''} "
            f"{location.get('plotSector') or ''} "
            f"row {location.get('row') or ''} "
            f"plant {location.get('plantNumber') or ''}"
        ),
        f"Address: {location.get('address') or 'not available'}",
    ]
    return '\n'.join(parts)
