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


class ConsultationRecord(Base):
    __tablename__ = "consultation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    evaluation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sample_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_annotations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    response_versions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    active_version_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    session: Mapped[BatchSession] = relationship(back_populates="items")
