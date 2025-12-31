from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LLM_PROVIDER: str = "openai"
    MODEL_NAME: str = "gpt-4o-mini"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    DB_URL: str = "sqlite:///data/jomuni.sqlite"
    EMBED_MODEL: str = "e5-small-v2"
    RAG_ENABLED: bool = False
    LANG: str = "nl"
    SESSION_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
