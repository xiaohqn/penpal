from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConsultationRecord(Base):
    __tablename__ = "consultation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    counselor_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False, default="default")
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    selected_persona_name: Mapped[str] = mapped_column(String(100), nullable=False)
    selected_style_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    planner_output_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    draft_candidates_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    ai_selected_raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    expert_polished_response: Mapped[str] = mapped_column(Text, nullable=False)
    expert_annotation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rag_ready: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sample_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sample_tags_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    planner_labels_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    risk_assessment_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evaluation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sample_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_annotations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    response_versions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    batch_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class BatchSession(Base):
    __tablename__ = "batch_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    counselor_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False, default="default")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    items: Mapped[list["BatchSessionItem"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="BatchSessionItem.row_number",
    )


class BatchSessionItem(Base):
    __tablename__ = "batch_session_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("batch_sessions.id"), index=True, nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    selected_persona_names_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    selected_persona_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    selected_style_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    planner_output_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    draft_candidates_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    ai_selected_raw_response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    latest_response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expert_annotation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rag_ready: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sample_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sample_tags_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    planner_labels_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    risk_assessment_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evaluation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sample_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_annotations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    response_versions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    active_version_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mail_thread_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    session: Mapped[BatchSession] = relationship(back_populates="items")


class WorkspaceTask(Base):
    __tablename__ = "workspace_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    counselor_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False, default="default")
    mode: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="single")
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="draft")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名工单")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    batch_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class UserLetter(Base):
    __tablename__ = "user_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    signature: Mapped[str] = mapped_column(String(100), nullable=False, default="匿名")
    letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    reply_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reply_source: Mapped[str] = mapped_column(String(32), nullable=False, default="ai")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="replied")
    response_preference: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    assigned_counselor_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class MailThread(Base):
    __tablename__ = "mail_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    signature: Mapped[str] = mapped_column(String(100), nullable=False, default="匿名")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="给心灵笔友的信")
    reply_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="ai")
    response_preference: Mapped[str] = mapped_column(String(64), nullable=False, default="温柔陪伴")
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="waiting_ai")
    assigned_counselor_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    messages: Mapped[list["MailMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="MailMessage.created_at",
    )
    memory: Mapped["ConversationMemory | None"] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        uselist=False,
    )
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="RiskAssessment.created_at",
    )


class MailMessage(Base):
    __tablename__ = "mail_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("mail_threads.id"), index=True, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    thread: Mapped[MailThread] = relationship(back_populates="messages")


class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("mail_threads.id"), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    thread: Mapped[MailThread] = relationship(back_populates="memory")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    thread_id: Mapped[int] = mapped_column(ForeignKey("mail_threads.id"), index=True, nullable=False)
    message_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user_letter")
    risk_level: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="NONE")
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    categories_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    signals_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    thread: Mapped[MailThread] = relationship(back_populates="risk_assessments")
