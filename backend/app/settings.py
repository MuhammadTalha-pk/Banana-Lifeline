from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_env: str = 'development'
    api_prefix: str = '/api/v1'
    cors_origins: str = '*'

    banana_ai_root: Path | None = None
    banana_model_checkpoint: Path | None = None
    vision_min_confidence: float = Field(0.75, ge=0.0, le=1.0)

    firebase_project_id: str | None = None
    google_application_credentials: Path | None = None

    # Zero-billing media storage. Files are stored on the FastAPI host.
    media_dir: Path = Path('./uploads')

    knowledge_dir: Path = Path('./knowledge')
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_local_path: Path = Path('./.qdrant')
    qdrant_collection: str = 'banana_lifeline_knowledge'
    embedding_model: str = 'BAAI/bge-m3'
    rag_top_k: int = 5

    deepseek_api_key: str | None = None
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-v4-flash'

    speech_enabled: bool = True

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == '*':
            return ['*']
        return [
            item.strip()
            for item in self.cors_origins.split(',')
            if item.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
