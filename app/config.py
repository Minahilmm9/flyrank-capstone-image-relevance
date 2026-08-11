"""
Central settings. Everything the app needs from the environment lives here —
nowhere else should call os.environ directly. This is what makes the
"secrets live in .env, never in code" rule easy to keep.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./data/app.db"

    gemini_vision_model: str = "gemini-3.1-flash-lite"
    gemini_vision_model_fallback: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"

    mismatch_similarity_threshold: float = 0.55
    mismatch_confidence_threshold: float = 0.5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()