from __future__ import annotations

from google.cloud import speech_v1 as speech
from google.oauth2 import service_account

from .settings import get_settings


class SpeechNotReady(RuntimeError):
    pass


def _speech_client() -> speech.SpeechClient:
    settings = get_settings()
    if settings.google_application_credentials:
        path = settings.google_application_credentials.expanduser().resolve()
        if not path.is_file():
            raise SpeechNotReady(
                f'Google service-account JSON does not exist: {path}'
            )
        creds = service_account.Credentials.from_service_account_file(str(path))
        return speech.SpeechClient(credentials=creds)
    return speech.SpeechClient()


def transcribe_wav(content: bytes, *, language: str) -> str:
    settings = get_settings()
    if not settings.speech_enabled:
        raise SpeechNotReady('Speech transcription is disabled.')

    locale = 'ur-PK' if language == 'ur' else 'en-PK'
    try:
        client = _speech_client()
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=locale,
            model='default',
            enable_automatic_punctuation=True,
        )
        response = client.recognize(config=config, audio=audio)
    except SpeechNotReady:
        raise
    except Exception as exc:
        raise SpeechNotReady(
            'Google Cloud Speech-to-Text is not available. Enable the API and verify service-account permissions.'
        ) from exc

    transcript = ' '.join(
        result.alternatives[0].transcript.strip()
        for result in response.results
        if result.alternatives
    ).strip()
    if not transcript:
        raise SpeechNotReady('No speech could be transcribed from the audio.')
    return transcript
