from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import BatchSession, BatchSessionItem
from app.schemas.record import (
    BatchExcelRow,
    BatchSessionCreateRequest,
    BatchSessionDetailResponse,
    BatchSessionItemDetail,
    BatchSessionItemUpdateRequest,
    BatchSessionListItem,
    BatchSessionListResponse,
)
from app.services.rag_service import RagService


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BatchSessionService:
    def __init__(self, rag_service: RagService | None = None):
        self.rag_service = rag_service or RagService()

    def _derive_rag_ready(
        self,
        expert_annotation: str,
        source_annotations: list[dict[str, Any]],
    ) -> str:
        if expert_annotation.strip() or source_annotations:
            return "approved"
        return "pending"

    def create_session(
        self,
        db: Session,
        payload: BatchSessionCreateRequest,
    ) -> BatchSessionDetailResponse:
        title = (payload.title or "").strip() or self._build_default_title(payload.source_file_name)
        session = BatchSession(
            title=title,
            source_file_name=payload.source_file_name,
            status="in_progress",
            total_items=len(payload.items),
            completed_items=0,
        )
        db.add(session)
        db.flush()

        items: list[BatchSessionItem] = []
        for item in payload.items:
            items.append(
                BatchSessionItem(
                    session_id=session.id,
                    row_number=item.row_number,
                    user_input=item.user_input,
                    status="pending",
                )
            )
        db.add_all(items)
        db.flush()

        if items:
            session.current_item_id = items[0].id

        db.commit()
        return self.get_session_detail(db, session.id)

    def list_sessions(self, db: Session) -> BatchSessionListResponse:
        total = db.scalar(select(func.count()).select_from(BatchSession)) or 0
        sessions = db.scalars(select(BatchSession).order_by(desc(BatchSession.updated_at))).all()
        return BatchSessionListResponse(
            items=[
                BatchSessionListItem(
                    id=session.id,
                    title=session.title,
                    source_file_name=session.source_file_name,
                    status=session.status,
                    total_items=session.total_items,
                    completed_items=session.completed_items,
                    current_item_id=session.current_item_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
                for session in sessions
            ],
            total=total,
        )

    def get_session_detail(self, db: Session, session_id: int) -> BatchSessionDetailResponse:
        session = db.scalar(
            select(BatchSession)
            .options(selectinload(BatchSession.items))
            .where(BatchSession.id == session_id)
        )
        if session is None:
            raise ValueError("Batch session not found")

        return BatchSessionDetailResponse(
            id=session.id,
            title=session.title,
            source_file_name=session.source_file_name,
            status=session.status,
            total_items=session.total_items,
            completed_items=session.completed_items,
            current_item_id=session.current_item_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            items=[self._to_item_detail(item) for item in session.items],
        )

    def update_item(
        self,
        db: Session,
        session_id: int,
        item_id: int,
        payload: BatchSessionItemUpdateRequest,
    ) -> BatchSessionDetailResponse:
        item = self._get_item(db, session_id, item_id)
        item.selected_persona_names_json = payload.selected_persona_names
        item.selected_persona_name = payload.selected_persona_name
        item.selected_style_config_json = payload.selected_style_config
        item.planner_output_json = payload.planner_output
        item.draft_candidates_json = payload.draft_candidates
        item.ai_selected_raw_response = payload.ai_selected_raw_response
        item.latest_response = payload.latest_response
        item.expert_annotation = payload.expert_annotation
        item.rag_ready = self._derive_rag_ready(payload.expert_annotation, payload.source_annotations)
        item.sample_reason = payload.sample_reason
        item.planner_labels_json = payload.planner_labels or self.rag_service.build_planner_labels(payload.planner_output)
        item.sample_tags_json = payload.sample_tags or self.rag_service.build_sample_tags(
            user_input=item.user_input,
            planner_output=payload.planner_output,
            expert_annotation=payload.expert_annotation,
            source_annotations=payload.source_annotations,
        )
        item.evaluation_json = payload.evaluation
        item.sample_snapshot_json = payload.sample_snapshot
        item.source_annotations_json = payload.source_annotations
        item.response_versions_json = payload.response_versions
        item.active_version_index = payload.active_version_index
        item.status = payload.status
        item.record_id = payload.record_id
        self._refresh_session_progress(db, item.session_id, preferred_current_item_id=item.id)
        db.commit()
        return self.get_session_detail(db, session_id)

    def append_response_version(
        self,
        db: Session,
        session_id: int,
        item_id: int,
        version: dict[str, Any],
        latest_response: str,
        planner_output: dict[str, Any],
        drafts: list[dict[str, Any]],
        ai_selected_raw_response: str,
        selected_persona_name: str,
        selected_persona_names: list[str],
        selected_style_config: dict[str, Any],
        source_annotations: list[dict[str, Any]],
        expert_annotation: str,
    ) -> BatchSessionDetailResponse:
        item = self._get_item(db, session_id, item_id)
        versions = list(item.response_versions_json or [])
        versions.append(version)
        item.response_versions_json = versions
        item.active_version_index = len(versions) - 1
        item.latest_response = latest_response
        item.planner_output_json = planner_output
        item.draft_candidates_json = drafts
        item.ai_selected_raw_response = ai_selected_raw_response
        item.selected_persona_name = selected_persona_name
        item.selected_persona_names_json = selected_persona_names
        item.selected_style_config_json = selected_style_config
        item.source_annotations_json = source_annotations
        item.expert_annotation = expert_annotation
        item.evaluation_json = {}
        item.status = "in_progress"
        self._refresh_session_progress(db, item.session_id, preferred_current_item_id=item.id)
        db.commit()
        return self.get_session_detail(db, session_id)

    def rollback_item_version(
        self,
        db: Session,
        session_id: int,
        item_id: int,
        version_index: int,
    ) -> BatchSessionDetailResponse:
        item = self._get_item(db, session_id, item_id)
        versions = list(item.response_versions_json or [])
        if version_index < 0 or version_index >= len(versions):
            raise ValueError("Version index out of range")

        version = versions[version_index]
        item.active_version_index = version_index
        item.latest_response = str(version.get("response", item.latest_response))
        item.selected_persona_name = str(version.get("selected_persona_name", item.selected_persona_name))
        item.source_annotations_json = list(version.get("source_annotations", item.source_annotations_json))
        self._refresh_session_progress(db, item.session_id, preferred_current_item_id=item.id)
        db.commit()
        return self.get_session_detail(db, session_id)

    def _get_item(self, db: Session, session_id: int, item_id: int) -> BatchSessionItem:
        item = db.scalar(
            select(BatchSessionItem).where(
                BatchSessionItem.id == item_id,
                BatchSessionItem.session_id == session_id,
            )
        )
        if item is None:
            raise ValueError("Batch session item not found")
        return item

    def _refresh_session_progress(
        self,
        db: Session,
        session_id: int,
        preferred_current_item_id: int | None = None,
    ) -> None:
        session = db.get(BatchSession, session_id)
        if session is None:
            raise ValueError("Batch session not found")

        items = db.scalars(
            select(BatchSessionItem)
            .where(BatchSessionItem.session_id == session_id)
            .order_by(BatchSessionItem.row_number)
        ).all()
        session.total_items = len(items)
        session.completed_items = sum(1 for item in items if item.status == "completed")

        next_item = next((item for item in items if item.status != "completed"), None)
        if preferred_current_item_id is not None:
            preferred = next((item for item in items if item.id == preferred_current_item_id), None)
            if preferred is not None and preferred.status != "completed":
                next_item = preferred

        session.current_item_id = next_item.id if next_item else (items[-1].id if items else None)
        session.status = "completed" if items and session.completed_items == len(items) else "in_progress"

    def _build_default_title(self, source_file_name: str) -> str:
        file_name = source_file_name.strip()
        if file_name:
            return f"批量任务 · {file_name}"
        return f"批量任务 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    def _to_item_detail(self, item: BatchSessionItem) -> BatchSessionItemDetail:
        return BatchSessionItemDetail(
            id=item.id,
            session_id=item.session_id,
            row_number=item.row_number,
            user_input=item.user_input,
            status=item.status,
            selected_persona_names_json=item.selected_persona_names_json or [],
            selected_persona_name=item.selected_persona_name,
            selected_style_config_json=item.selected_style_config_json or {},
            planner_output_json=item.planner_output_json or {},
            draft_candidates_json=item.draft_candidates_json or [],
            ai_selected_raw_response=item.ai_selected_raw_response,
            latest_response=item.latest_response,
            expert_annotation=item.expert_annotation,
            rag_ready=item.rag_ready,
            sample_reason=item.sample_reason,
            sample_tags_json=item.sample_tags_json or {},
            planner_labels_json=item.planner_labels_json or {},
            evaluation_json=item.evaluation_json or {},
            sample_snapshot_json=item.sample_snapshot_json or {},
            source_annotations_json=item.source_annotations_json or [],
            response_versions_json=item.response_versions_json or [],
            active_version_index=item.active_version_index,
            record_id=item.record_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
