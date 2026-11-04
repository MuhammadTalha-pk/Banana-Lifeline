from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .settings import get_settings


_ALLOWED_EXTENSIONS = {
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.wav',
    '.m4a',
    '.aac',
    '.mp3',
    '.ogg',
}


def _root() -> Path:
    root = get_settings().media_dir.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_media(
    *,
    uid: str,
    kind: str,
    content: bytes,
    original_name: str | None,
    default_extension: str,
) -> tuple[str, Path]:
    if not content:
        raise ValueError('Uploaded file is empty.')

    ext = Path(original_name or '').suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        ext = default_extension

    safe_kind = ''.join(c for c in kind if c.isalnum() or c in {'-', '_'}) or 'media'
    folder = _root() / uid / safe_kind
    folder.mkdir(parents=True, exist_ok=True)

    name = f'{uuid4().hex}{ext}'
    path = folder / name
    path.write_bytes(content)

    relative = path.relative_to(_root()).as_posix()
    return relative, path


def load_media(relative_path: str) -> bytes:
    root = _root()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError('Invalid media path.') from exc
    if not candidate.is_file():
        raise FileNotFoundError(relative_path)
    return candidate.read_bytes()


def public_media_url(base_url: str, relative_path: str) -> str:
    root = base_url.rstrip('/')
    return f'{root}/media/{relative_path}'
