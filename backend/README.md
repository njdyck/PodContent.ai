# PodContent.ai — Backend

FastAPI Backend für die Audio → Content Pipeline.

## Setup

```bash
# 1. Virtual Environment erstellen
cd backend
python -m venv venv
source venv/bin/activate

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Environment Variablen konfigurieren
cp .env.example .env
# → .env mit echten Keys befüllen

# 4. Server starten
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### `GET /health`
Health Check → `{"status": "ok"}`

### `POST /upload`
Audio-Datei hochladen und Content generieren.

**Request** (multipart/form-data):
| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|-------------|
| `file` | File | ✅ | Audio-Datei (mp3, wav, m4a) |
| `user_id` | String | ✅ | Supabase Auth User ID |
| `title` | String | ❌ | Episode-Titel (default: "Unbenannte Episode") |

**Response:**
```json
{
  "episode_id": "uuid",
  "transcript_word_count": 1234,
  "content_count": 5,
  "content_types": ["linkedin_post", "blog_article", "newsletter", "tweet_thread", "show_notes"],
  "status": "completed"
}
```

### `GET /docs`
Swagger UI — interaktive API-Dokumentation.

## Projektstruktur

```
backend/
├── app/
│   ├── main.py              # FastAPI App + CORS
│   ├── config.py            # Settings (.env)
│   ├── api/
│   │   └── upload.py        # POST /upload Route
│   ├── services/
│   │   ├── supabase.py      # DB + Storage Operations
│   │   ├── transcription.py # Whisper API
│   │   └── content.py       # LLM Content Generation
│   └── prompts/
│       └── system_prompt.py # System Prompt
├── requirements.txt
├── .env.example
└── README.md
```
