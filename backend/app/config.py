from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://piping:piping@localhost:5432/piping_cms"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480
    debug: bool = False
    cors_origins: str = "http://localhost:5173"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
