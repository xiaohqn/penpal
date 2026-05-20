from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsultationRecordSaveRequest(BaseModel):
    user_input: str = Field(min_length=1)
    selected_persona_name: str = Field(min_length=1)
    selected_style_config: dict[str, Any]
    planner_output: dict[str, Any]
    draft_candidates: list[dict[str, Any]] = Field(min_length=1)
    ai_selected_raw_response: str = Field(min_length=1)
    expert_polished_response: str = Field(min_length=1)
    expert_annotation: str = ""
    rag_ready: str = "pending"
    sample_reason: str = ""
    sample_snapshot: dict[str, Any] = Field(default_factory=dict)
    source_annotations: list[dict[str, Any]] = Field(default_factory=list)
    response_versions: list[dict[str, Any]] = Field(default_factory=list)
    batch_session_id: int | None = None
    batch_item_id: int | None = None

    @field_validator("user_input", "selected_persona_name", "ai_selected_raw_response", "expert_polished_response")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field cannot be empty")
        return cleaned

    @field_validator("expert_annotation", "sample_reason")
    @classmethod
    def strip_optional_annotation(cls, value: str) -> str:
        return value.strip()

    @field_validator("rag_ready")
    @classmethod
    def validate_rag_ready(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"pending", "approved", "rejected"}:
            raise ValueError("rag_ready must be one of: pending, approved, rejected")
        return normalized


class ConsultationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_input: str
    selected_persona_name: str
    selected_style_config_json: dict[str, Any]
    planner_output_json: dict[str, Any]
    draft_candidates_json: list[dict[str, Any]]
    ai_selected_raw_response: str
    expert_polished_response: str
    expert_annotation: str
    rag_ready: str
    sample_reason: str
    sample_snapshot_json: dict[str, Any]
    source_annotations_json: list[dict[str, Any]]
    response_versions_json: list[dict[str, Any]]
    batch_session_id: int | None
    batch_item_id: int | None
    created_at: datetime
    updated_at: datetime


class ConsultationRecordListItem(BaseModel):
    id: int
    user_input: str
    selected_persona_name: str
    expert_annotation: str
    rag_ready: str
    sample_reason: str
    created_at: datetime
    updated_at: datetime


class ConsultationRecordListResponse(BaseModel):
    items: list[ConsultationRecordListItem]
    total: int
    page: int
    page_size: int


class BatchExcelRow(BaseModel):
    row_number: int
    user_input: str
    selected_persona_names: list[str] = Field(default_factory=list)


class BatchExcelImportResponse(BaseModel):
    items: list[BatchExcelRow]
    total: int


class BatchGenerateRequest(BaseModel):
    items: list[BatchExcelRow] = Field(min_length=1, max_length=200)


class BatchGenerateRecord(BaseModel):
    row_number: int
    user_input: str
    selected_persona_names: list[str]
    draft_count: int
    drafts: list[dict[str, Any]]


class ReviewedBatchItem(BaseModel):
    row_number: int
    user_input: str
    selected_persona_name: str
    final_response: str
    expert_annotation: str = ""
    rag_ready: str = "pending"
    sample_reason: str = ""
    source_annotations: list[dict[str, Any]] = Field(default_factory=list)
    active_version_index: int = 0


class SourceAnnotationNote(BaseModel):
    id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str = ""
    note: str = ""
    color: str = "amber"


class ResponseVersion(BaseModel):
    version_index: int = Field(ge=0)
    label: str = ""
    response: str = ""
    selected_persona_name: str = ""
    created_at: str = ""
    source: str = "manual"
    source_annotations: list[SourceAnnotationNote] = Field(default_factory=list)


class BatchSessionCreateRequest(BaseModel):
    title: str | None = None
    source_file_name: str = ""
    items: list[BatchExcelRow] = Field(min_length=1, max_length=2000)


class BatchSessionListItem(BaseModel):
    id: int
    title: str
    source_file_name: str
    status: str
    total_items: int
    completed_items: int
    current_item_id: int | None
    created_at: datetime
    updated_at: datetime


class BatchSessionListResponse(BaseModel):
    items: list[BatchSessionListItem]
    total: int


class BatchSessionItemDetail(BaseModel):
    id: int
    session_id: int
    row_number: int
    user_input: str
    status: str
    selected_persona_names_json: list[str]
    selected_persona_name: str
    selected_style_config_json: dict[str, Any]
    planner_output_json: dict[str, Any]
    draft_candidates_json: list[dict[str, Any]]
    ai_selected_raw_response: str
    latest_response: str
    expert_annotation: str
    rag_ready: str
    sample_reason: str
    sample_snapshot_json: dict[str, Any]
    source_annotations_json: list[dict[str, Any]]
    response_versions_json: list[dict[str, Any]]
    active_version_index: int
    record_id: int | None
    created_at: datetime
    updated_at: datetime


class BatchSessionDetailResponse(BaseModel):
    id: int
    title: str
    source_file_name: str
    status: str
    total_items: int
    completed_items: int
    current_item_id: int | None
    created_at: datetime
    updated_at: datetime
    items: list[BatchSessionItemDetail]


class BatchSessionItemUpdateRequest(BaseModel):
    selected_persona_names: list[str] = Field(default_factory=list)
    selected_persona_name: str = ""
    selected_style_config: dict[str, Any] = Field(default_factory=dict)
    planner_output: dict[str, Any] = Field(default_factory=dict)
    draft_candidates: list[dict[str, Any]] = Field(default_factory=list)
    ai_selected_raw_response: str = ""
    latest_response: str = ""
    expert_annotation: str = ""
    rag_ready: str = "pending"
    sample_reason: str = ""
    sample_snapshot: dict[str, Any] = Field(default_factory=dict)
    source_annotations: list[dict[str, Any]] = Field(default_factory=list)
    response_versions: list[dict[str, Any]] = Field(default_factory=list)
    active_version_index: int = 0
    status: str = "in_progress"
    record_id: int | None = None


class BatchSessionItemRegenerateRequest(BaseModel):
    selected_persona_name: str = Field(min_length=1)
    selected_persona_names: list[str] = Field(default_factory=list)
    source_annotations: list[SourceAnnotationNote] = Field(default_factory=list)
    expert_annotation: str = ""
    current_response: str = ""


class BatchSessionItemRollbackRequest(BaseModel):
    version_index: int = Field(ge=0)


class ReviewedBatchExportRequest(BaseModel):
    items: list[ReviewedBatchItem] = Field(min_length=1, max_length=2000)
