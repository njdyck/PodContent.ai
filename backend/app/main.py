"""PodContent.ai — FastAPI Application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="PodContent.ai",
    description="Podcast → Content Pipeline: Audio hochladen, transkribieren, Content generieren.",
    version="0.1.0",
)


@app.on_event("startup")
def configure_cors():
    """Load settings and configure CORS at startup."""
    from app.config import get_settings
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Routes ───────────────────────────────────────────────────────
app.include_router(upload_router, tags=["Pipeline"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
