from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserLetterCreateRequest(BaseModel):
    signature: str = "匿名"
    letter_text: str = Field(min_length=1)
    reply_text: str = ""
    reply_source: str = "ai"
    status: str = "replied"
    response_preference: str = ""

    @field_validator("signature", "reply_text", "reply_source", "status", "response_preference")
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("letter_text")
    @classmethod
    def strip_letter_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("letter_text cannot be empty")
        return cleaned


class UserLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    signature: str
    letter_text: str
    reply_text: str
    reply_source: str
    status: str
    response_preference: str
    assigned_counselor_id: str | None
    created_at: datetime
    updated_at: datetime


class UserLetterListResponse(BaseModel):
    items: list[UserLetterResponse]
    total: int


class UserLetterStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1)

    @field_validator("status")
    @classmethod
    def strip_status(cls, value: str) -> str:
        return value.strip()


class CounselorReplyRequest(BaseModel):
    reply_text: str = Field(min_length=1)

    @field_validator("reply_text")
    @classmethod
    def strip_reply_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reply_text cannot be empty")
        return cleaned
