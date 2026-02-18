"""Content generation service — single LLM call for all content formats."""

import json

from openai import OpenAI

from app.config import get_settings
from app.prompts.system_prompt import SYSTEM_PROMPT


def generate_content(transcript_text: str) -> dict:
    """Generate all 5 content formats from a transcript.

    Sends a single GPT-4o call with the system prompt and transcript.
    Returns the parsed JSON dict with all content types.
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Hier ist das Transkript einer Podcast-Episode. "
                    "Generiere daraus alle Content-Formate.\n\n"
                    "---TRANSKRIPT---\n"
                    f"{transcript_text}\n"
                    "---ENDE---"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)
