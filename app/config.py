"""Configuracao da aplicacao, lida do .env e do ambiente.

O .env tambem e carregado em os.environ porque o Google ADK/GenAI le a chave
(GOOGLE_API_KEY) diretamente do ambiente do processo.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=False)
if not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
    # Usamos a API do Google AI Studio, nao o Vertex AI.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"


class Settings(BaseSettings):
    # env_ignore_empty: uma variavel presente mas vazia no .env usa o padrao.
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    postgres_user: str = "aurora"
    postgres_password: str = "aurora"
    postgres_db: str = "aurora"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    modelo_principal: str = ""
    modelo_especialistas: str = ""

    ambiente: str = "desenvolvimento"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def producao(self) -> bool:
        return self.ambiente.strip().lower() in {"producao", "produção", "production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
