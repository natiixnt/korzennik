from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./korzennik.db"
    familysearch_app_key: str = ""
    geneteka_delay_seconds: float = 1.5
    debug: bool = False

    model_config = {"env_file": ".env", "env_prefix": "KORZENNIK_"}


settings = Settings()
