from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import ConsultationRecord
from app.schemas.record import (
    ConsultationRecordListItem,
    ConsultationRecordListResponse,
    ConsultationRecordResponse,
    ConsultationRecordSaveRequest,
)


class RecordService:
    def _derive_rag_ready(self, payload: ConsultationRecordSaveRequest) -> str:
        if payload.expert_annotation.strip() or payload.source_annotations:
            return "approved"
        return "pending"

    def create_record(
        self,
        db: Session,
        payload: ConsultationRecordSaveRequest,
    ) -> ConsultationRecordResponse:
        record = ConsultationRecord(
            user_input=payload.user_input,
            selected_persona_name=payload.selected_persona_name,
            selected_style_config_json=payload.selected_style_config,
            planner_output_json=payload.planner_output,
            draft_candidates_json=payload.draft_candidates,
            ai_selected_raw_response=payload.ai_selected_raw_response,
            expert_polished_response=payload.expert_polished_response,
            expert_annotation=payload.expert_annotation,
            rag_ready=self._derive_rag_ready(payload),
            sample_reason=payload.sample_reason,
            sample_snapshot_json=payload.sample_snapshot,
            source_annotations_json=payload.source_annotations,
            response_versions_json=payload.response_versions,
            batch_session_id=payload.batch_session_id,
            batch_item_id=payload.batch_item_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return ConsultationRecordResponse.model_validate(record)

    def list_records(
        self,
        db: Session,
        page: int,
        page_size: int,
    ) -> ConsultationRecordListResponse:
        total = db.scalar(select(func.count()).select_from(ConsultationRecord)) or 0
        offset = (page - 1) * page_size
        records = db.scalars(
            select(ConsultationRecord)
            .order_by(desc(ConsultationRecord.created_at))
            .offset(offset)
            .limit(page_size)
        ).all()

        items = [
            ConsultationRecordListItem(
                id=record.id,
                user_input=record.user_input,
                selected_persona_name=record.selected_persona_name,
                expert_annotation=record.expert_annotation,
                rag_ready=record.rag_ready,
                sample_reason=record.sample_reason,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
            for record in records
        ]
        return ConsultationRecordListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_record(self, db: Session, record_id: int) -> ConsultationRecordResponse | None:
        record = db.get(ConsultationRecord, record_id)
        if record is None:
            return None
        return ConsultationRecordResponse.model_validate(record)

    def get_all_records_for_export(self, db: Session) -> list[dict]:
        records = db.scalars(
            select(ConsultationRecord).order_by(desc(ConsultationRecord.created_at))
        ).all()
        return [ConsultationRecordResponse.model_validate(record).model_dump() for record in records]
