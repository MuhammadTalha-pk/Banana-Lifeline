"""Tests for credential loading.

The case-insensitivity here is not cosmetic. A ``.env`` written by hand on Windows with
``DeepSeek_API_KEY`` resolves fine locally, because Windows environment lookups ignore case.
The Colab GPU box and CI are Linux, where it would silently return ``None`` and the failure
would surface as an unexplained auth error far from its cause.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from banana_lifeline.secrets import ServiceCredentials, _parse_env_file


def _write_env(tmp_path: Path, body: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(body, encoding="utf-8")
    return path


def test_parses_simple_assignments(tmp_path: Path) -> None:
    env = _parse_env_file(_write_env(tmp_path, "A=1\nB=two\n"))
    assert env == {"A": "1", "B": "two"}


def test_strips_quotes_and_whitespace(tmp_path: Path) -> None:
    env = _parse_env_file(_write_env(tmp_path, "A = \"quoted\" \nB='single'\n"))
    assert env == {"A": "quoted", "B": "single"}


def test_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    env = _parse_env_file(_write_env(tmp_path, "# comment\n\nA=1\n#B=2\n"))
    assert env == {"A": "1"}


def test_ignores_lines_without_an_equals(tmp_path: Path) -> None:
    env = _parse_env_file(_write_env(tmp_path, "nonsense\nA=1\n"))
    assert env == {"A": "1"}


def test_skips_empty_values(tmp_path: Path) -> None:
    """An unset placeholder must not read as configured."""
    env = _parse_env_file(_write_env(tmp_path, "A=\nB=2\n"))
    assert env == {"B": "2"}


def test_missing_file_is_not_an_error(tmp_path: Path) -> None:
    assert _parse_env_file(tmp_path / "absent.env") == {}


def test_key_lookup_ignores_case(monkeypatch: pytest.MonkeyPatch) -> None:
    """`DeepSeek_API_KEY` must resolve the same as `DEEPSEEK_API_KEY`."""
    import banana_lifeline.secrets as secrets

    secrets._environment.cache_clear()
    monkeypatch.setenv("DeepSeek_API_KEY", "sk-test")

    try:
        assert secrets.get_secret("DEEPSEEK_API_KEY") == "sk-test"
    finally:
        secrets._environment.cache_clear()


def test_credentials_report_presence_not_values() -> None:
    credentials = ServiceCredentials(
        deepseek_api_key="sk-secret",
        deepseek_base_url="https://api.deepseek.com",
        qdrant_url=None,
        qdrant_api_key="qdrant-secret",
    )
    assert credentials.has_deepseek is True
    assert credentials.has_qdrant is False  # a key without a URL cannot connect


def test_require_deepseek_explains_how_to_fix() -> None:
    credentials = ServiceCredentials(
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        qdrant_url=None,
        qdrant_api_key=None,
    )
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        credentials.require_deepseek()


def test_require_deepseek_returns_the_key_when_present() -> None:
    credentials = ServiceCredentials(
        deepseek_api_key="sk-test",
        deepseek_base_url="https://api.deepseek.com",
        qdrant_url=None,
        qdrant_api_key=None,
    )
    assert credentials.require_deepseek() == "sk-test"


def test_env_file_is_gitignored() -> None:
    """Regression guard: a committed API key is unrecoverable once pushed."""
    from banana_lifeline.config import get_paths

    gitignore = get_paths().ai_root / ".gitignore"
    assert gitignore.is_file(), "ai/.gitignore is missing"
    assert ".env" in gitignore.read_text(encoding="utf-8").splitlines()
