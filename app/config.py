import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central, environment-driven configuration for the entire API."""

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    GEMINI_FALLBACK_MODELS: list[str] = [
        m.strip()
        for m in os.getenv(
            "GEMINI_FALLBACK_MODELS",
            "gemini-3.6-flash,gemini-3.5-flash-lite",
        ).split(",")
        if m.strip()
    ]

    # Hackathon kill switch: when true, bypass Gemini entirely and return the
    # deterministic fallback plan. Flip via Render env var — no redeploy needed.
    FORCE_FALLBACK: bool = os.getenv("FORCE_FALLBACK", "false").lower() == "true"

    APP_NAME: str = "Celebration & Event Planner API"
    APP_VERSION: str = "1.0.0"


settings = Settings()