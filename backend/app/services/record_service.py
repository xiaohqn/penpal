from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import ConsultationRecord
from app.schemas.record import (
    ConsultationRecordListItem,
    ConsultationRecordListResponse,
    ConsultationRecordResponse,
    ConsultationRecordSaveRequest,
    ConsultationRecordUpdateRequest,
)
from app.services.rag_service import RagService


class RecordService:
    def __init__(self, rag_service: RagService | None = None):
        self.rag_service = rag_service or RagService()

    def _derive_rag_ready(self, payload: ConsultationRecordSaveRequest) -> str:
        return "approved"

    def create_record(
        self,
        db: Session,
        payload: ConsultationRecordSaveRequest,
        counselor_id: str = "default",
    ) -> ConsultationRecordResponse:
        planner_labels = payload.planner_labels or self.rag_service.build_planner_labels(payload.planner_output)
        sample_tags = payload.sample_tags or self.rag_service.build_sample_tags(
            user_input=payload.user_input,
            planner_output=payload.planner_output,
            expert_annotation=payload.expert_annotation,
            source_annotations=payload.source_annotations,
        )
        record = None
        if payload.workspace_task_id is not None:
            record = db.scalar(
                select(ConsultationRecord).where(
                    ConsultationRecord.counselor_id == counselor_id,
                    ConsultationRecord.workspace_task_id == payload.workspace_task_id,
                    ConsultationRecord.user_input == payload.user_input,
                )
            )
        elif payload.batch_item_id is not None:
            record = db.scalar(
                select(ConsultationRecord).where(
                    ConsultationRecord.counselor_id == counselor_id,
                    ConsultationRecord.batch_item_id == payload.batch_item_id,
                )
            )
        if record is None:
            record = ConsultationRecord(counselor_id=counselor_id, user_input=payload.user_input)
            db.add(record)

        record.user_input = payload.user_input
        record.selected_persona_name = payload.selected_persona_name
        record.selected_style_config_json = payload.selected_style_config
        record.planner_output_json = payload.planner_output
        record.draft_candidates_json = payload.draft_candidates
        record.ai_selected_raw_response = payload.ai_selected_raw_response
        record.expert_polished_response = payload.expert_polished_response
        record.expert_annotation = payload.expert_annotation
        record.rag_ready = self._derive_rag_ready(payload)
        record.sample_reason = payload.sample_reason
        record.sample_tags_json = sample_tags
        record.planner_labels_json = planner_labels
        record.risk_assessment_json = payload.risk_assessment
        record.evaluation_json = payload.evaluation
        record.sample_snapshot_json = payload.sample_snapshot
        record.source_annotations_json = payload.source_annotations
        record.response_versions_json = payload.response_versions
        record.workspace_task_id = payload.workspace_task_id
        record.batch_session_id = payload.batch_session_id
        record.batch_item_id = payload.batch_item_id
        db.commit()
        db.refresh(record)
        return ConsultationRecordResponse.model_validate(record)

    def list_records(
        self,
        db: Session,
        page: int,
        page_size: int,
        counselor_id: str = "default",
        include_all: bool = False,
    ) -> ConsultationRecordListResponse:
        filters = [] if include_all else [ConsultationRecord.counselor_id == counselor_id]
        total_query = select(func.count()).select_from(ConsultationRecord)
        if filters:
            total_query = total_query.where(*filters)
        total = db.scalar(total_query) or 0
        offset = (page - 1) * page_size
        query = select(ConsultationRecord)
        if filters:
            query = query.where(*filters)
        records = db.scalars(query.order_by(desc(ConsultationRecord.created_at)).offset(offset).limit(page_size)).all()

        items = [
            ConsultationRecordListItem(
                id=record.id,
                counselor_id=record.counselor_id,
                user_input=record.user_input,
                selected_persona_name=record.selected_persona_name,
                expert_annotation=record.expert_annotation,
                rag_ready=record.rag_ready,
                sample_reason=record.sample_reason,
                sample_tags_json=record.sample_tags_json or {},
                planner_labels_json=record.planner_labels_json or {},
                risk_assessment_json=record.risk_assessment_json or {},
                evaluation_json=record.evaluation_json or {},
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

    def get_record(
        self,
        db: Session,
        record_id: int,
        counselor_id: str = "default",
        include_all: bool = False,
    ) -> ConsultationRecordResponse | None:
        record = db.get(ConsultationRecord, record_id)
        if record is None:
            return None
        if not include_all and record.counselor_id != counselor_id:
            return None
        return ConsultationRecordResponse.model_validate(record)

    def update_record(
        self,
        db: Session,
        record_id: int,
        payload: ConsultationRecordUpdateRequest,
        counselor_id: str = "default",
        include_all: bool = False,
    ) -> ConsultationRecordResponse | None:
        record = db.get(ConsultationRecord, record_id)
        if record is None:
            return None
        if not include_all and record.counselor_id != counselor_id:
            return None

        if payload.user_input is not None:
            record.user_input = payload.user_input
        if payload.expert_polished_response is not None:
            record.expert_polished_response = payload.expert_polished_response
        if payload.expert_annotation is not None:
            record.expert_annotation = payload.expert_annotation
        if payload.rag_ready is not None:
            record.rag_ready = payload.rag_ready
        if payload.sample_reason is not None:
            record.sample_reason = payload.sample_reason
        if payload.sample_tags is not None:
            record.sample_tags_json = payload.sample_tags
        if payload.planner_labels is not None:
            record.planner_labels_json = payload.planner_labels
        if payload.evaluation is not None:
            record.evaluation_json = payload.evaluation

        db.commit()
        db.refresh(record)
        return ConsultationRecordResponse.model_validate(record)

    def get_all_records_for_export(
        self,
        db: Session,
        counselor_id: str = "default",
        include_all: bool = False,
    ) -> list[dict]:
        query = select(ConsultationRecord)
        if not include_all:
            query = query.where(ConsultationRecord.counselor_id == counselor_id)
        records = db.scalars(query.order_by(desc(ConsultationRecord.created_at))).all()
        return [ConsultationRecordResponse.model_validate(record).model_dump() for record in records]
