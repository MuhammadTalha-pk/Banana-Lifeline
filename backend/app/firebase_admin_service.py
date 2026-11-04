from __future__ import annotations

from functools import lru_cache

import firebase_admin
from firebase_admin import auth, credentials, firestore

from .settings import get_settings


@lru_cache(maxsize=1)
def ensure_firebase() -> firebase_admin.App:
    if firebase_admin._apps:
        return firebase_admin.get_app()

    settings = get_settings()
    options = {}
    if settings.firebase_project_id:
        options['projectId'] = settings.firebase_project_id

    credential = None
    if settings.google_application_credentials:
        path = settings.google_application_credentials.expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(
                f'Google/Firebase service-account JSON does not exist: {path}'
            )
        credential = credentials.Certificate(str(path))

    return firebase_admin.initialize_app(credential=credential, options=options or None)


def db() -> firestore.Client:
    ensure_firebase()
    return firestore.client()


def verify_bearer_token(token: str) -> dict:
    ensure_firebase()
    return auth.verify_id_token(token, check_revoked=True)
