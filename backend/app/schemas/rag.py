from typing import Any

from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    user_input: str = Field(min_length=1)
    planner_output: dict[str, Any] = Field(default_factory=dict)
    persona_name: str = ""
    limit: int = Field(default=3, ge=1, le=10)


class RagSampleResponse(BaseModel):
    id: int
    source: str
    score: float
    selected_persona_name: str
    user_input: str
    expert_response: str
    expert_annotation: str
    sample_tags: dict[str, Any]
    planner_labels: dict[str, Any]


class RagSearchResponse(BaseModel):
    items: list[RagSampleResponse]
