"""Configurações da aplicação via variáveis de ambiente."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://piping:piping@localhost:5432/piping_cms"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
