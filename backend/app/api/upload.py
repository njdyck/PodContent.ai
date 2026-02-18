"""POST /upload — Main pipeline endpoint.

Receives an audio file + user_id, runs the full pipeline:
Upload → Transcribe → Generate Content → Save to Supabase.
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.config import get_settings
from app.services import supabase as db
from app.services.transcription import transcribe
from app.services.content import generate_content

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_episode(
    file: UploadFile = File(..., description="Audio file (mp3, wav, m4a, etc.)"),
    user_id: str = Form(..., description="Supabase Auth user ID"),
    title: str = Form(default="Unbenannte Episode", description="Episode title"),
):
    """Full pipeline: Audio upload → Transcription → Content generation.

    Returns the episode ID and all generated content.
    """
    settings = get_settings()

    # ── Validate file size ───────────────────────────────────────
    audio_bytes = await file.read()
    max_bytes = settings.max_audio_size_mb * 1024 * 1024

    if len(audio_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large. Maximum: {settings.max_audio_size_mb}MB",
        )

    episode_id = None

    try:
        # 1. Upload audio to Supabase Storage
        logger.info("Uploading audio to storage...")
        storage_path = db.upload_audio(user_id, audio_bytes, file.filename)

        # 2. Create episode in DB
        logger.info("Creating episode...")
        episode_id = db.create_episode(user_id, title, storage_path)

        # 3. Transcribe with Whisper
        logger.info("Transcribing audio...")
        db.update_episode_status(episode_id, "transcribing")
        transcript_text = transcribe(audio_bytes, file.filename)
        word_count = len(transcript_text.split())

        # 4. Save transcript
        logger.info("Saving transcript...")
        db.save_transcript(episode_id, transcript_text, word_count)

        # 5. Generate content with LLM
        logger.info("Generating content...")
        db.update_episode_status(episode_id, "generating")
        contents = generate_content(transcript_text)

        # 6. Save all content formats
        logger.info("Saving content...")
        content_ids = db.save_contents(episode_id, contents)

        # 7. Mark as completed
        db.update_episode_status(episode_id, "completed")
        logger.info("Pipeline completed for episode %s", episode_id)

        return {
            "episode_id": episode_id,
            "transcript_word_count": word_count,
            "content_count": len(content_ids),
            "content_types": list(contents.keys()),
            "status": "completed",
        }

    except Exception as e:
        logger.error("Pipeline failed: %s", str(e))
        if episode_id:
            db.update_episode_status(episode_id, "failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
