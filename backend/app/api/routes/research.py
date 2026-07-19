import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.api.auth import get_counselor_id
from app.api.deps import get_db_session, get_research_event_service
from app.schemas.research import ResearchEventCreate, ResearchEventResponse
from app.services.research_event_service import ResearchEventService

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/events", response_model=ResearchEventResponse)
def create_event(payload: ResearchEventCreate, counselor_id: str = Depends(get_counselor_id), db: Session = Depends(get_db_session), service: ResearchEventService = Depends(get_research_event_service)) -> ResearchEventResponse:
    return service.create(db, counselor_id, payload)


@router.get("/events/export")
def export_events(scope: str = "mine", counselor_id: str = Depends(get_counselor_id), db: Session = Depends(get_db_session), service: ResearchEventService = Depends(get_research_event_service)) -> Response:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "research_events"
    sheet.append(["event_id", "created_at", "counselor_id", "event_type", "workspace_task_id", "batch_session_id", "batch_item_id", "record_id", "planner_changes_json", "before_text", "after_text", "diff_json", "annotations_json", "metadata_json"])
    for event in service.list_for_export(db, counselor_id, include_all=scope == "all"):
        is_planner = event.event_type == "planner_regenerate"
        metadata = event.metadata_json or {}
        planner_changes = service.build_field_changes(metadata.get("planner_before", {}), metadata.get("planner_after", {})) if is_planner else []
        sheet.append([event.id, event.created_at.isoformat(), event.counselor_id, event.event_type, event.workspace_task_id, event.batch_session_id, event.batch_item_id, event.record_id, json.dumps(planner_changes, ensure_ascii=False), "" if is_planner else event.before_text, "" if is_planner else event.after_text, "" if is_planner else json.dumps(event.diff_json, ensure_ascii=False), "" if is_planner else json.dumps(event.annotations_json, ensure_ascii=False), json.dumps({"persona_name": metadata.get("persona_name", "")} if is_planner else metadata, ensure_ascii=False)])
    output = io.BytesIO()
    workbook.save(output)
    return Response(content=output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="research_events.xlsx"'})
