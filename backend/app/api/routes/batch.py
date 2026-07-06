import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_counselor_id
from app.api.deps import (
    get_batch_session_service,
    get_db_session,
    get_excel_service,
    get_mail_thread_service,
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
from app.db.models import BatchSession, BatchSessionItem
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.mail_thread_service import MailThreadService
from app.services.orchestration_service import OrchestrationService
from app.services.record_service import RecordService

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post("/import", response_model=BatchSessionDetailResponse)
async def import_batch_excel(
    file: UploadFile = File(...),
    counselor_id: str = Depends(get_counselor_id),
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
            counselor_id=counselor_id,
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
    scope: str = "mine",
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    record_service: RecordService = Depends(get_record_service),
    excel_service: ExcelService = Depends(get_excel_service),
) -> Response:
    records = record_service.get_all_records_for_export(
        db=db,
        counselor_id=counselor_id,
        include_all=scope == "all",
    )
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
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionListResponse:
    return batch_session_service.list_sessions(db=db, counselor_id=counselor_id)


@router.get("/sessions/{session_id}", response_model=BatchSessionDetailResponse)
def get_batch_session(
    session_id: int,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        return batch_session_service.get_session_detail(db=db, session_id=session_id, counselor_id=counselor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/sessions/{session_id}/items/{item_id}/current", response_model=BatchSessionDetailResponse)
def set_current_batch_session_item(
    session_id: int,
    item_id: int,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        return batch_session_service.set_current_item(
            db=db,
            session_id=session_id,
            item_id=item_id,
            counselor_id=counselor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/sessions/{session_id}/items/{item_id}", response_model=BatchSessionDetailResponse)
def update_batch_session_item(
    session_id: int,
    item_id: int,
    payload: BatchSessionItemUpdateRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> BatchSessionDetailResponse:
    try:
        previous_item = db.scalar(
            select(BatchSessionItem)
            .join(BatchSession)
            .where(
                BatchSessionItem.id == item_id,
                BatchSessionItem.session_id == session_id,
                BatchSession.counselor_id == counselor_id,
            )
        )
        was_completed = previous_item.status == "completed" if previous_item is not None else False
        detail = batch_session_service.update_item(
            db=db,
            session_id=session_id,
            item_id=item_id,
            payload=payload,
            counselor_id=counselor_id,
        )
        updated_item = next((item for item in detail.items if item.id == item_id), None)
        should_send_reply = (
            updated_item
            and updated_item.mail_thread_id
            and payload.status == "completed"
            and not was_completed
            and payload.latest_response.strip()
        )
        if should_send_reply:
            mail_thread_service.submit_counselor_reply_text(
                db=db,
                counselor_id=counselor_id,
                thread_id=updated_item.mail_thread_id,
                content=payload.latest_response.strip(),
            )
        return detail
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/items/{item_id}/rollback", response_model=BatchSessionDetailResponse)
def rollback_batch_session_item(
    session_id: int,
    item_id: int,
    payload: BatchSessionItemRollbackRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        return batch_session_service.rollback_item_version(
            db=db,
            session_id=session_id,
            item_id=item_id,
            version_index=payload.version_index,
            counselor_id=counselor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/items/{item_id}/regenerate", response_model=BatchSessionDetailResponse)
async def regenerate_batch_session_item(
    session_id: int,
    item_id: int,
    payload: BatchSessionItemRegenerateRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    try:
        session = batch_session_service.get_session_detail(db=db, session_id=session_id, counselor_id=counselor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    item = next((current for current in session.items if current.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Batch session item not found")

    annotation_block = _build_annotation_block(payload.source_annotations)
    augmented_user_input = _build_generation_input(item.user_input, item.context_json)
    if payload.current_response.strip():
        augmented_user_input += f"\n\n【当前 AI 回复】\n{payload.current_response.strip()}"
    if annotation_block:
        augmented_user_input += (
            f"\n\n【专家对当前 AI 回复的高亮批注】\n{annotation_block}\n\n"
            "请基于上述 AI 回复内容进行重写和修正，优先处理这些被高亮的回复片段，让新版本更符合专家意图。"
        )
    if payload.expert_annotation.strip():
        augmented_user_input += f"\n\n【专家总体说明】\n{payload.expert_annotation.strip()}"

    selected_draft = await orchestration_service.generate_from_plan(
        user_input=augmented_user_input,
        persona_name=payload.selected_persona_name,
        planner_output=payload.planner_output or item.planner_output_json or {},
        use_deep_thinking=payload.use_deep_thinking,
    )
    if selected_draft is None:
        raise HTTPException(status_code=400, detail="No draft generated")
    drafts = [selected_draft]

    existing_versions = list(item.response_versions_json or [])
    version = {
        "version_index": len(existing_versions),
        "label": f"批注重生成 v{len(existing_versions) + 1}",
        "response": selected_draft["response"],
        "selected_persona_name": payload.selected_persona_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "annotation_regenerate",
        "source_annotations": [annotation.model_dump() for annotation in payload.source_annotations],
        "safety_review": selected_draft.get("safety_review", {}),
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
        selected_persona_name=selected_draft["persona_name"],
        selected_persona_names=payload.selected_persona_names or [payload.selected_persona_name],
        selected_style_config=selected_draft.get("style_config", {}),
        source_annotations=[annotation.model_dump() for annotation in payload.source_annotations],
        expert_annotation=payload.expert_annotation,
        counselor_id=counselor_id,
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


def _build_generation_input(user_input: str, context: dict | None) -> str:
    if not context or context.get("kind") != "mail_thread_reply":
        return user_input
    risk = context.get("risk") or {}
    transcript_items = context.get("transcript") or []
    transcript = "\n\n".join(
        f"{item.get('label') or '书信'}：\n{item.get('content') or ''}"
        for item in transcript_items
        if isinstance(item, dict)
    )
    memory_summary = "\n".join(
        line for line in str(context.get("memory_summary") or "").splitlines() if not line.strip().startswith("风险趋势：")
    ).strip()
    risk_level = str(risk.get("level") or "NONE") if isinstance(risk, dict) else "NONE"
    risk_signals = risk.get("signals") if isinstance(risk, dict) else []
    risk_reasoning = str(risk.get("reasoning") or "") if isinstance(risk, dict) else ""
    risk_block = ""
    if risk_level != "NONE":
        signals_text = "；".join(str(signal) for signal in risk_signals) if isinstance(risk_signals, list) else risk_reasoning
        risk_block = f"【风险提示】\n等级：{risk_level}\n触发因素：{signals_text or risk_reasoning or '无'}"
    parts = [
        "【当前用户来信】",
        user_input,
        f"【系统记忆摘要】\n{memory_summary}" if memory_summary else "",
        risk_block,
        "【统一回应策略】理性分析",
        f"【用户署名】{context.get('signature') or '匿名'}",
        f"【完整书信往返】\n{transcript}" if transcript else "",
        str(
            context.get("instruction")
            or "请为咨询师生成一封可审阅修改后发送给用户的书信式回信。需要参考完整上下文和风险提示；不要声称自己是 AI；不要替代医疗诊断或治疗。"
        ),
    ]
    return "\n\n".join(part for part in parts if part.strip())
