from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResearchEvent
from app.schemas.research import ResearchEventCreate, ResearchEventResponse


class ResearchEventService:
    def create(self, db: Session, counselor_id: str, payload: ResearchEventCreate) -> ResearchEventResponse:
        event = ResearchEvent(
            counselor_id=counselor_id,
            event_type=payload.event_type.strip(),
            workspace_task_id=payload.workspace_task_id,
            batch_session_id=payload.batch_session_id,
            batch_item_id=payload.batch_item_id,
            record_id=payload.record_id,
            before_text=payload.before_text,
            after_text=payload.after_text,
            diff_json=self.build_diff(payload.before_text, payload.after_text),
            annotations_json=payload.annotations,
            metadata_json=payload.metadata,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return ResearchEventResponse.model_validate(event)

    def list_for_export(self, db: Session, counselor_id: str, include_all: bool = False) -> list[ResearchEvent]:
        query = select(ResearchEvent)
        if not include_all:
            query = query.where(ResearchEvent.counselor_id == counselor_id)
        return list(db.scalars(query.order_by(ResearchEvent.created_at, ResearchEvent.id)).all())

    @staticmethod
    def build_diff(before: str, after: str) -> list[dict[str, object]]:
        changes: list[dict[str, object]] = []
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, before, after).get_opcodes():
            if tag == "equal":
                continue
            changes.append({
                "operation": tag,
                "before_start": i1,
                "before_end": i2,
                "after_start": j1,
                "after_end": j2,
                "before": before[i1:i2],
                "after": after[j1:j2],
            })
        return changes

    @classmethod
    def build_field_changes(cls, before: object, after: object, prefix: str = "") -> list[dict[str, object]]:
        """Return only changed Planner leaf fields, with dotted field paths."""
        if isinstance(before, dict) and isinstance(after, dict):
            changes: list[dict[str, object]] = []
            for key in sorted(set(before) | set(after)):
                path = f"{prefix}.{key}" if prefix else str(key)
                changes.extend(cls.build_field_changes(before.get(key), after.get(key), path))
            return changes
        if before == after:
            return []
        return [{"field": prefix, "before": before, "after": after}]
