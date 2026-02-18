"""Supabase service — handles all database and storage operations."""

import uuid
from typing import Dict, List, Optional

from supabase import create_client, Client

from app.config import get_settings


def get_client() -> Client:
    """Create and return a Supabase client using the service role key."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# ── Storage ──────────────────────────────────────────────────────

def upload_audio(user_id: str, file_bytes: bytes, filename: str) -> str:
    """Upload audio file to Supabase Storage.

    Files are stored under: audio/{user_id}/{uuid}_{filename}
    Returns the storage path.
    """
    client = get_client()
    safe_name = filename.replace(" ", "_")
    storage_path = f"{user_id}/{uuid.uuid4().hex[:8]}_{safe_name}"

    client.storage.from_("audio").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "audio/mpeg"},
    )

    return storage_path


def download_audio(storage_path: str) -> bytes:
    """Download audio file from Supabase Storage."""
    client = get_client()
    return client.storage.from_("audio").download(storage_path)


# ── Episodes ─────────────────────────────────────────────────────

def create_episode(user_id: str, title: str, audio_storage_path: str) -> str:
    """Create a new episode and return its ID."""
    client = get_client()
    result = (
        client.table("episodes")
        .insert({
            "user_id": user_id,
            "title": title,
            "audio_storage_path": audio_storage_path,
            "status": "uploaded",
        })
        .execute()
    )
    return result.data[0]["id"]


def update_episode_status(
    episode_id: str, status: str, error_message: Optional[str] = None
) -> None:
    """Update the status of an episode."""
    client = get_client()
    update_data: Dict[str, str] = {"status": status}
    if error_message:
        update_data["error_message"] = error_message

    client.table("episodes").update(update_data).eq("id", episode_id).execute()


# ── Transcripts ──────────────────────────────────────────────────

def save_transcript(episode_id: str, full_text: str, word_count: int) -> str:
    """Save a transcript and return its ID."""
    client = get_client()
    result = (
        client.table("transcripts")
        .insert({
            "episode_id": episode_id,
            "full_text": full_text,
            "language": "de",
            "word_count": word_count,
        })
        .execute()
    )
    return result.data[0]["id"]


# ── Contents ─────────────────────────────────────────────────────

CONTENT_TYPES = [
    "linkedin_post",
    "blog_article",
    "newsletter",
    "tweet_thread",
    "show_notes",
]


def save_contents(episode_id: str, contents: dict) -> List[str]:
    """Save all generated content formats for an episode.

    `contents` is the parsed JSON dict from the LLM (keys = content_type).
    Returns list of created content IDs.
    """
    client = get_client()
    rows = []
    for content_type in CONTENT_TYPES:
        if content_type not in contents:
            continue
        item = contents[content_type]
        rows.append({
            "episode_id": episode_id,
            "content_type": content_type,
            "title": item.get("title", ""),
            "body": item["body"],
            "metadata": item.get("metadata", {}),
        })

    result = client.table("contents").insert(rows).execute()
    return [row["id"] for row in result.data]
