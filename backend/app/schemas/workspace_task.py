from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceTaskSaveRequest(BaseModel):
    mode: str = "single"
    status: str = "draft"
    title: str = ""
    summary: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    batch_session_id: int | None = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"single", "excel_batch", "mail_batch", "manual"}:
            raise ValueError("mode must be one of: single, excel_batch, mail_batch, manual")
        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"draft", "in_progress", "completed", "archived"}:
            raise ValueError("status must be one of: draft, in_progress, completed, archived")
        return normalized

    @field_validator("title", "summary")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class WorkspaceTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    counselor_id: str
    mode: str
    status: str
    title: str
    summary: str
    state_json: dict[str, Any]
    batch_session_id: int | None
    created_at: datetime
    updated_at: datetime


class WorkspaceTaskListResponse(BaseModel):
    items: list[WorkspaceTaskResponse]
    total: int
