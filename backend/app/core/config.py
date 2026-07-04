from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app.db"
DEFAULT_RAG_SEED_PATH = PROJECT_ROOT / "data" / "seed.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
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
    counselor_generator_model: str = ""
    user_generator_model: str = ""
    planner_timeout_seconds: int = 90
    generator_timeout_seconds: int = 180
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
    local_generator_max_new_tokens: int = 1536
    local_top_p: float = 0.9

    mock_llm: bool = True
    stream_chunk_size: int = 28
    stream_chunk_delay_ms: int = 15
    generator_extra_body: dict[str, Any] = Field(default_factory=dict)
    counselor_generator_extra_body: dict[str, Any] = Field(default_factory=dict)
    user_generator_extra_body: dict[str, Any] = Field(default_factory=dict)
    rag_enabled: bool = True
    rag_seed_path: str = str(DEFAULT_RAG_SEED_PATH)
    rag_seed_enabled: bool = True
    counselor_features_enabled: bool = True
    visitor_invite_codes: list[str] = Field(default_factory=list)
    counselor_invite_codes: list[str] = Field(default_factory=list)
    active_counselor_ids: list[str] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("visitor_invite_codes", "counselor_invite_codes", "active_counselor_ids", mode="before")
    @classmethod
    def parse_invite_codes(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("generator_extra_body", "counselor_generator_extra_body", "user_generator_extra_body", mode="before")
    @classmethod
    def parse_generator_extra_body(cls, value: str | dict[str, Any] | None) -> dict[str, Any]:
        if value is None or value == "":
            return {}
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError("GENERATOR_EXTRA_BODY must be a JSON object")
            return parsed
        return value

    @property
    def effective_counselor_generator_model(self) -> str:
        return self.counselor_generator_model or self.generator_model

    @property
    def effective_user_generator_model(self) -> str:
        return self.user_generator_model or self.generator_model

    @property
    def effective_counselor_generator_extra_body(self) -> dict[str, Any]:
        return self.counselor_generator_extra_body or self.generator_extra_body

    @property
    def effective_user_generator_extra_body(self) -> dict[str, Any]:
        return self.user_generator_extra_body or self.generator_extra_body

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
