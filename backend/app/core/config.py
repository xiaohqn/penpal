from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app.db"
DEFAULT_RAG_SEED_PATH = PROJECT_ROOT.parent / "data" / "seed.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mindful Copilot API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH}"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    planner_model: str = "gpt-4o-mini"
    generator_model: str = "doubao-1-5-pro-32k-250115"
    planner_mode: Literal["auto", "mock", "api"] = "auto"
    generator_mode: Literal["auto", "mock", "api", "local", "vllm"] = "auto"
    compare_model_outputs: bool = False

    gpt_api_key: str | None = None
    gpt_base_url: str = "https://api.chatanywhere.tech/v1"
    doubao_api_key: str | None = None
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    vllm_api_key: str | None = None
    vllm_base_url: str = "http://127.0.0.1:8001/v1"
    vllm_model_name: str = ""

    local_model_path: str | None = None
    local_generator_model_path: str | None = None
    local_device: str = "auto"
    local_dtype: str = "auto"
    local_trust_remote_code: bool = True
    local_generator_max_new_tokens: int = 1024
    local_top_p: float = 0.9

    mock_llm: bool = True
    stream_chunk_size: int = 28
    stream_chunk_delay_ms: int = 15
    rag_seed_path: str = str(DEFAULT_RAG_SEED_PATH)
    rag_seed_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def effective_planner_mode(self) -> Literal["mock", "api"]:
        if self.planner_mode != "auto":
            return self.planner_mode
        if self.mock_llm or not self.gpt_api_key:
            return "mock"
        return "api"

    @property
    def effective_generator_mode(self) -> Literal["mock", "api", "local", "vllm"]:
        if self.generator_mode != "auto":
            return self.generator_mode
        if self.mock_llm:
            return "mock"
        if self.vllm_model_name:
            return "vllm"
        if self.local_generator_model_path or self.local_model_path:
            return "local"
        if self.doubao_api_key:
            return "api"
        return "mock"

    @property
    def use_mock_llm(self) -> bool:
        return self.effective_planner_mode == "mock" and self.effective_generator_mode == "mock"

    def resolve_local_generator_model_path(self) -> Path | None:
        raw_path = self.local_generator_model_path or self.local_model_path
        if not raw_path:
            return None
        return Path(raw_path).expanduser()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
