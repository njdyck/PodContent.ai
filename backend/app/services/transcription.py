"""Transcription service — uses OpenAI Whisper API."""

import io

from openai import OpenAI

from app.config import get_settings


def transcribe(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio bytes using OpenAI Whisper.

    Returns the transcript as plain text.
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    # Whisper expects a file-like object with a name attribute
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="de",
        response_format="text",
    )

    return response
