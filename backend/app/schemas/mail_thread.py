from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.record import BatchSessionDetailResponse
from app.schemas.time import serialize_datetime


FROM_ATTRIBUTES_CONFIG = ConfigDict(from_attributes=True)


class DateTimeResponseModel(BaseModel):
    model_config = FROM_ATTRIBUTES_CONFIG

    @field_serializer("*", when_used="json")
    def serialize_datetimes(self, value: object) -> object:
        if isinstance(value, datetime):
            return serialize_datetime(value)
        return value


RESPONSE_PREFERENCES = {"温柔陪伴", "理性分析", "启发引导"}


class MailMessageResponse(DateTimeResponseModel):
    id: int
    thread_id: int
    sender_type: str
    sender_id: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime


class ConversationMemoryResponse(DateTimeResponseModel):
    id: int
    thread_id: int
    user_id: str
    summary: str
    message_count: int
    updated_at: datetime


class RiskAssessmentResponse(DateTimeResponseModel):
    id: int
    user_id: str
    thread_id: int
    message_id: int | None
    target_type: str
    risk_level: str
    confidence: float
    categories: list[str] = Field(validation_alias="categories_json", serialization_alias="categories")
    signals: list[str] = Field(validation_alias="signals_json", serialization_alias="signals")
    reasoning: str
    reviewed: bool
    created_at: datetime


class MailThreadResponse(DateTimeResponseModel):
    id: int
    user_id: str
    signature: str
    title: str
    reply_mode: str
    response_preference: str
    status: str
    assigned_counselor_id: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MailMessageResponse] = []
    memory: ConversationMemoryResponse | None = None
    risk_assessments: list[RiskAssessmentResponse] = []


class MailThreadListResponse(BaseModel):
    items: list[MailThreadResponse]
    total: int


class MailThreadArchiveResponse(BaseModel):
    record_id: int
    rag_ready: str


class MailThreadCreateRequest(BaseModel):
    signature: str = "匿名"
    content: str = Field(min_length=1)
    reply_mode: str = "ai"
    response_preference: str = "温柔陪伴"
    ai_reply_text: str = ""

    @field_validator("signature", "reply_mode", "response_preference", "ai_reply_text")
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content cannot be empty")
        return cleaned

    @field_validator("reply_mode")
    @classmethod
    def validate_reply_mode(cls, value: str) -> str:
        if value not in {"ai", "human"}:
            raise ValueError("reply_mode must be ai or human")
        return value

    @field_validator("response_preference")
    @classmethod
    def validate_response_preference(cls, value: str) -> str:
        if value not in RESPONSE_PREFERENCES:
            raise ValueError("response_preference is not supported")
        return value


class MailMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    ai_reply_text: str = ""

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content cannot be empty")
        return cleaned

    @field_validator("ai_reply_text")
    @classmethod
    def strip_ai_reply_text(cls, value: str) -> str:
        return value.strip()


class CounselorThreadReplyRequest(BaseModel):
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content cannot be empty")
        return cleaned


class MailThreadWorkspaceSessionResponse(BatchSessionDetailResponse):
    pass
