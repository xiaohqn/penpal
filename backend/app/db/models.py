from __future__ import annotations

"""
输入：
- SQLAlchemy 在应用启动时会读取这里的 ORM 模型定义，并结合 `Settings.database_url` 连接到目标数据库。
- 各个 service 会向这些模型写入人格回信记录、批量处理记录或安全回复记录。
输出：
- 导出 `Base`、`ConsultationRecord`、`BatchSession`、`BatchSessionItem`、`SafetyReplyRecord` 等 ORM 模型，
  供建表、查询和持久化使用。
作用：
- 这个文件集中定义项目的数据库表，是后端持久化层的单一事实来源。
- 目前同时承载普通人格回信记录、批量会话记录和安全回复记录，方便前端分别查看和复用不同类型样本。
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    """返回带 UTC 时区的当前时间，供数据库默认值与更新时间字段复用。"""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """项目所有 ORM 模型的基类。"""
    pass


class ConsultationRecord(Base):
    """
    输入：
    - 来自普通人格回信工作流的原始来信、选中人格、Planner 输出、AI 草稿、专家润色稿与批注元数据。
    输出：
    - 在 `consultation_records` 表中持久化一条完整的人格回信记录。
    作用：
    - 保存常规人格生成链路的高质量训练样本，供后续 few-shot / RAG 复用。
    """

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
    """
    输入：
    - 一次批量 Excel 导入任务的标题、来源文件名、总体进度和当前处理项。
    输出：
    - 在 `batch_sessions` 表中持久化批量任务的全局状态。
    作用：
    - 让批量处理流程可以跨刷新恢复，并支持逐条推进、回看与导出。
    """

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
    """
    输入：
    - 某个批量任务中的单条来信、候选人格、草稿、版本、批注和保存状态等细节。
    输出：
    - 在 `batch_session_items` 表中持久化该条批量处理项的完整工作进度。
    作用：
    - 为批量工作流提供逐条可恢复、可回退、可重生成的数据基础。
    """

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


class SafetyReplyRecord(Base):
    """
    输入：
    - 来自安全回复工作流的原始来信、模型识别出的风险类型、人工修正后的风险类型、风险原因、
      原始安全回复与专家润色后的安全回复，以及安全回复候选、专家批注、划词批注和版本历史等过程数据。
    输出：
    - 在 `safety_reply_records` 表中持久化一条安全回复记录。
    作用：
    - 为高风险来信建立独立的安全回复样本库，并尽量保留接近普通对话历史页的完整处理过程。
    """

    __tablename__ = "safety_reply_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    style_name: Mapped[str] = mapped_column(String(50), default="安全", nullable=False)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    risk_labels_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    corrected_risk_labels_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    risk_reason: Mapped[str] = mapped_column(Text, nullable=False)
    ai_safe_response: Mapped[str] = mapped_column(Text, nullable=False)
    expert_polished_response: Mapped[str] = mapped_column(Text, nullable=False)
    selected_response_source: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    selected_response_source_label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    safe_response_candidates_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    expert_annotation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sample_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_annotations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    response_versions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
