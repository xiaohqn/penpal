from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    workspace_task_id: int | None = None
    batch_session_id: int | None = None
    batch_item_id: int | None = None
    record_id: int | None = None
    before_text: str = ""
    after_text: str = ""
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    counselor_id: str
    event_type: str
    workspace_task_id: int | None
    batch_session_id: int | None
    batch_item_id: int | None
    record_id: int | None
    before_text: str
    after_text: str
    diff_json: list[dict[str, Any]]
    annotations_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]
    created_at: datetime
