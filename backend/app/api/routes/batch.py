import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import (
    get_batch_session_service,
    get_db_session,
    get_excel_service,
    get_orchestration_service,
    get_record_service,
)
from app.schemas.record import (
    BatchGenerateRequest,
    BatchGenerateRecord,
    BatchSessionCreateRequest,
    BatchSessionDetailResponse,
    BatchSessionItemRollbackRequest,
    BatchSessionItemUpdateRequest,
    BatchSessionListResponse,
    BatchSessionItemRegenerateRequest,
    ReviewedBatchExportRequest,
)
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.orchestration_service import OrchestrationService
from app.services.record_service import RecordService

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post("/import", response_model=BatchSessionDetailResponse)
async def import_batch_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
    excel_service: ExcelService = Depends(get_excel_service),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    content = await file.read()
    try:
        parsed = excel_service.parse_batch_import(content)
        return batch_session_service.create_session(
            db=db,
            payload=BatchSessionCreateRequest(
                source_file_name=file.filename or "",
                items=parsed.items,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate/export")
async def batch_generate_export(
    payload: BatchGenerateRequest,
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
    excel_service: ExcelService = Depends(get_excel_service),
) -> Response:
    results: list[dict] = []

    for item in payload.items:
        drafts = await orchestration_service.generate_all(
            user_input=item.user_input,
            persona_names=item.selected_persona_names,
        )
        results.append(
            BatchGenerateRecord(
                row_number=item.row_number,
                user_input=item.user_input,
                selected_persona_names=item.selected_persona_names,
                draft_count=len(drafts),
                drafts=drafts,
            ).model_dump()
        )

    content = excel_service.export_batch_generation_excel(results)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="batch_generation_results.xlsx"'},
    )


@router.get("/records/export")
def export_records_excel(
    db: Session = Depends(get_db_session),
    record_service: RecordService = Depends(get_record_service),
    excel_service: ExcelService = Depends(get_excel_service),
) -> Response:
    records = record_service.get_all_records_for_export(db=db)
    content = excel_service.export_records_excel(records)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="consultation_records.xlsx"'},
    )


@router.post("/reviewed/export")
def export_reviewed_batch_excel(
    payload: ReviewedBatchExportRequest,
    excel_service: ExcelService = Depends(get_excel_service),
) -> Response:
    content = excel_service.export_reviewed_batch_excel(
        [item.model_dump() for item in payload.items]
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reviewed_batch_results.xlsx"'},
    )


@router.get("/sessions", response_model=BatchSessionListResponse)
def list_batch_sessions(
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionListResponse:
    return batch_session_service.list_sessions(db=db)


@router.get("/sessions/{session_id}", response_model=BatchSessionDetailResponse)
def get_batch_session(
    session_id: int,
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        return batch_session_service.get_session_detail(db=db, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/sessions/{session_id}/items/{item_id}", response_model=BatchSessionDetailResponse)
def update_batch_session_item(
    session_id: int,
    item_id: int,
    payload: BatchSessionItemUpdateRequest,
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        return batch_session_service.update_item(
            db=db,
            session_id=session_id,
            item_id=item_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/items/{item_id}/rollback", response_model=BatchSessionDetailResponse)
def rollback_batch_session_item(
    session_id: int,
    item_id: int,
    payload: BatchSessionItemRollbackRequest,
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        return batch_session_service.rollback_item_version(
            db=db,
            session_id=session_id,
            item_id=item_id,
            version_index=payload.version_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/items/{item_id}/regenerate", response_model=BatchSessionDetailResponse)
async def regenerate_batch_session_item(
    session_id: int,
    item_id: int,
    payload: BatchSessionItemRegenerateRequest,
    db: Session = Depends(get_db_session),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        session = batch_session_service.get_session_detail(db=db, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    item = next((current for current in session.items if current.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Batch session item not found")

    annotation_block = _build_annotation_block(payload.source_annotations)
    augmented_user_input = item.user_input
    if payload.current_response.strip():
        augmented_user_input += f"\n\n【当前 AI 回复】\n{payload.current_response.strip()}"
    if annotation_block:
        augmented_user_input += (
            f"\n\n【专家对当前 AI 回复的高亮批注】\n{annotation_block}\n\n"
            "请基于上述 AI 回复内容进行重写和修正，优先处理这些被高亮的回复片段，让新版本更符合专家意图。"
        )
    if payload.expert_annotation.strip():
        augmented_user_input += f"\n\n【专家总体说明】\n{payload.expert_annotation.strip()}"

    drafts = await orchestration_service.generate_all(
        user_input=augmented_user_input,
        persona_names=payload.selected_persona_names or [payload.selected_persona_name],
    )
    selected_draft = next(
        (draft for draft in drafts if draft["persona_name"] == payload.selected_persona_name),
        drafts[0] if drafts else None,
    )
    if selected_draft is None:
        raise HTTPException(status_code=400, detail="No draft generated")

    existing_versions = list(item.response_versions_json or [])
    version = {
        "version_index": len(existing_versions),
        "label": f"批注重生成 v{len(existing_versions) + 1}",
        "response": selected_draft["response"],
        "selected_persona_name": payload.selected_persona_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "annotation_regenerate",
        "source_annotations": [annotation.model_dump() for annotation in payload.source_annotations],
    }

    return batch_session_service.append_response_version(
        db=db,
        session_id=session_id,
        item_id=item_id,
        version=version,
        latest_response=selected_draft["response"],
        planner_output=selected_draft.get("planner_output", {}),
        drafts=drafts,
        ai_selected_raw_response=selected_draft.get("raw_response", ""),
        selected_persona_name=payload.selected_persona_name,
        selected_persona_names=payload.selected_persona_names or [payload.selected_persona_name],
        selected_style_config=selected_draft.get("style_config", {}),
        source_annotations=[annotation.model_dump() for annotation in payload.source_annotations],
        expert_annotation=payload.expert_annotation,
    )


def _build_annotation_block(annotations: list[object]) -> str:
    lines: list[str] = []
    for index, annotation in enumerate(annotations, start=1):
        quote = annotation.quote.strip() if annotation.quote else ""
        note = annotation.note.strip() if annotation.note else ""
        if not quote and not note:
            continue
        lines.append(f"{index}. 回复片段：{quote or '未填写'}；专家批注：{note or '未填写'}")
    return "\n".join(lines)
