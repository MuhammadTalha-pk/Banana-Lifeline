"""Credential loading for external services.

Secrets come from ``ai/.env`` (gitignored) or the process environment. Nothing here ever
logs, prints, or serialises a key value -- only whether one is present.

Environment variable names are matched case-insensitively on purpose. ``.env`` files get
written by hand with whatever casing felt natural at the time (``DeepSeek_API_KEY``,
``DEEPSEEK_API_KEY``, ``deepseek_api_key``), and Windows resolves those identically while
Linux does not. The Google Cloud GPU box and CI are Linux, so a key that works locally would
otherwise vanish the moment the code moves.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from banana_lifeline.config import get_paths

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Minimal ``.env`` parser: ``KEY=value``, ``#`` comments, optional quotes."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if value:
            values[key.strip()] = value
    return values


@lru_cache(maxsize=1)
def _environment() -> dict[str, str]:
    """Merge ``.env`` with the process environment, lower-cased for lookup.

    The real environment wins, so a CI secret overrides a stale local file.
    """
    merged = {k.lower(): v for k, v in _parse_env_file(get_paths().ai_root / ".env").items()}
    merged.update({k.lower(): v for k, v in os.environ.items()})
    return merged


def get_secret(*names: str) -> str | None:
    """First matching value among ``names``, compared case-insensitively."""
    env = _environment()
    for name in names:
        value = env.get(name.lower())
        if value:
            return value
    return None


@dataclass(frozen=True, slots=True)
class ServiceCredentials:
    """What is configured right now. Values are never rendered in logs or reports."""

    deepseek_api_key: str | None
    deepseek_base_url: str
    qdrant_url: str | None
    qdrant_api_key: str | None

    @property
    def has_deepseek(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def has_qdrant(self) -> bool:
        return bool(self.qdrant_url)

    def require_deepseek(self) -> str:
        if not self.deepseek_api_key:
            raise RuntimeError(
                "DeepSeek API key not found. Add DEEPSEEK_API_KEY=... to ai/.env "
                "or set it in the environment."
            )
        return self.deepseek_api_key


def load_credentials() -> ServiceCredentials:
    return ServiceCredentials(
        deepseek_api_key=get_secret("DEEPSEEK_API_KEY", "DEEPSEEK_KEY"),
        deepseek_base_url=get_secret("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL,
        qdrant_url=get_secret("QDRANT_URL"),
        qdrant_api_key=get_secret("QDRANT_API_KEY"),
    )
