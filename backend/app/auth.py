from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status
from firebase_admin import exceptions as firebase_exceptions

from .firebase_admin_service import verify_bearer_token


@dataclass(frozen=True, slots=True)
class AuthUser:
    uid: str
    email: str | None
    claims: dict


async def current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing Firebase bearer token.',
        )

    token = authorization.split(' ', 1)[1].strip()
    try:
        claims = verify_bearer_token(token)
    except (ValueError, firebase_exceptions.FirebaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired Firebase token.',
        ) from exc

    uid = str(claims.get('uid') or claims.get('sub') or '')
    if not uid:
        raise HTTPException(status_code=401, detail='Firebase token has no user id.')

    return AuthUser(uid=uid, email=claims.get('email'), claims=claims)
