from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DraftCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    draft_id: str = ""
    persona_name: str
    source: str = ""
    source_label: str = ""
    style_config: dict[str, str]
    planner_output: dict[str, Any]
    response: str
    raw_response: str = ""


class GenerationRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=5000)
    persona_names: list[str] = Field(min_length=1, max_length=5)
    compare_sources: bool = False
    source_mode: str = "auto"

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("user_input cannot be empty")
        return cleaned

    @field_validator("persona_names")
    @classmethod
    def validate_persona_names(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            name = item.strip()
            if name and name not in cleaned:
                cleaned.append(name)
        if not cleaned:
            raise ValueError("persona_names cannot be empty")
        return cleaned

    @field_validator("source_mode")
    @classmethod
    def validate_source_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"auto", "api", "vllm", "compare"}:
            raise ValueError("source_mode must be one of: auto, api, vllm, compare")
        return normalized


class GenerateFromPlanRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=8000)
    persona_name: str = Field(min_length=1)
    planner_output: dict[str, Any] = Field(default_factory=dict)
    source_mode: str = "auto"

    @field_validator("source_mode")
    @classmethod
    def validate_source_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"auto", "api", "vllm", "mock"}:
            raise ValueError("source_mode must be one of: auto, api, vllm, mock")
        return normalized


class StreamEvent(BaseModel):
    event: str
    draft_id: str | None = None
    persona_name: str | None = None
    source: str | None = None
    source_label: str | None = None
    planner_output: dict[str, Any] | None = None
    delta: str | None = None
    response: str | None = None
    message: str | None = None
    drafts: list[DraftCandidate] | None = None
