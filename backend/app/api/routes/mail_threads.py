from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.api.auth import get_counselor_id, get_user_id
from app.api.deps import get_batch_session_service, get_db_session, get_mail_thread_service, get_session_maker
from app.schemas.mail_thread import (
    CounselorThreadReplyRequest,
    MailThreadArchiveResponse,
    MailMessageCreateRequest,
    MailThreadCreateRequest,
    MailThreadListResponse,
    MailThreadResponse,
)
from app.schemas.record import BatchExcelRow, BatchSessionCreateRequest, BatchSessionDetailResponse
from app.services.batch_session_service import BatchSessionService
from app.services.mail_thread_service import MailThreadService

router = APIRouter(prefix="/mail-threads", tags=["mail-threads"])


async def _generate_ai_reply_background(
    session_maker: sessionmaker,
    mail_thread_service: MailThreadService,
    user_id: str,
    thread_id: int,
) -> None:
    db = session_maker()
    try:
        await mail_thread_service.generate_pending_ai_reply(db=db, user_id=user_id, thread_id=thread_id)
    finally:
        db.close()


@router.post("", response_model=MailThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_mail_thread(
    payload: MailThreadCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    session_maker: sessionmaker = Depends(get_session_maker),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadResponse:
    try:
        thread = await mail_thread_service.create_thread(db=db, user_id=user_id, payload=payload)
        if thread.status == "waiting_ai":
            background_tasks.add_task(_generate_ai_reply_background, session_maker, mail_thread_service, user_id, thread.id)
        return thread
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=MailThreadListResponse)
def list_mail_threads(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadListResponse:
    return mail_thread_service.list_threads(db=db, user_id=user_id)


@router.get("/assigned/mine", response_model=MailThreadListResponse)
def list_assigned_mail_threads(
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadListResponse:
    return mail_thread_service.list_assigned_threads(db=db, counselor_id=counselor_id)


@router.post("/assigned/workspace-session", response_model=BatchSessionDetailResponse)
def create_assigned_mail_threads_workspace_session(
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    threads = mail_thread_service.list_assigned_threads(db=db, counselor_id=counselor_id).items
    pending_threads = [thread for thread in threads if thread.status in {"waiting_counselor", "crisis"}]
    if not pending_threads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending assigned letters")
    existing_session = batch_session_service.find_assigned_threads_session(
        db=db,
        counselor_id=counselor_id,
        mail_thread_ids=[thread.id for thread in pending_threads],
    )
    if existing_session is not None:
        return existing_session
    return batch_session_service.create_session(
        db=db,
        counselor_id=counselor_id,
        payload=BatchSessionCreateRequest(
            title="人工书信批量回复",
            source_file_name="assigned-mail-threads",
            items=[
                BatchExcelRow(
                    row_number=index,
                    user_input=mail_thread_service.build_workspace_input(thread),
                    mail_thread_id=thread.id,
                    context=mail_thread_service.build_workspace_context(thread),
                )
                for index, thread in enumerate(pending_threads, start=1)
            ],
        ),
    )


@router.post("/assigned/{thread_id}/workspace-session", response_model=BatchSessionDetailResponse)
def create_assigned_mail_thread_workspace_session(
    thread_id: int,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
    batch_session_service: BatchSessionService = Depends(get_batch_session_service),
) -> BatchSessionDetailResponse:
    thread = mail_thread_service.get_assigned_thread(db=db, counselor_id=counselor_id, thread_id=thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned thread not found")
    existing_session = batch_session_service.find_mail_thread_session(
        db=db,
        counselor_id=counselor_id,
        mail_thread_id=thread.id,
    )
    if existing_session is not None:
        return existing_session
    return batch_session_service.create_session(
        db=db,
        counselor_id=counselor_id,
        payload=BatchSessionCreateRequest(
            title=f"人工书信回复 · {thread.title}",
            source_file_name="assigned-mail-thread",
            items=[
                BatchExcelRow(
                    row_number=1,
                    user_input=mail_thread_service.build_workspace_input(thread),
                    mail_thread_id=thread.id,
                    context=mail_thread_service.build_workspace_context(thread),
                )
            ],
        ),
    )


@router.post("/assigned/{thread_id}/reply", response_model=MailThreadResponse)
def submit_assigned_mail_thread_reply(
    thread_id: int,
    payload: CounselorThreadReplyRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadResponse:
    thread = mail_thread_service.submit_counselor_reply(
        db=db,
        counselor_id=counselor_id,
        thread_id=thread_id,
        payload=payload,
    )
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned thread not found")
    return thread


@router.get("/{thread_id}", response_model=MailThreadResponse)
def get_mail_thread(
    thread_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadResponse:
    thread = mail_thread_service.get_thread(db=db, user_id=user_id, thread_id=thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


@router.post("/{thread_id}/messages", response_model=MailThreadResponse, status_code=status.HTTP_201_CREATED)
async def add_mail_thread_message(
    thread_id: int,
    payload: MailMessageCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    session_maker: sessionmaker = Depends(get_session_maker),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadResponse:
    thread = await mail_thread_service.add_user_message(db=db, user_id=user_id, thread_id=thread_id, payload=payload)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if thread.status == "waiting_ai":
        background_tasks.add_task(_generate_ai_reply_background, session_maker, mail_thread_service, user_id, thread.id)
    return thread


@router.post("/{thread_id}/archive-ai-reply", response_model=MailThreadArchiveResponse)
def archive_ai_reply_to_records(
    thread_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadArchiveResponse:
    try:
        result = mail_thread_service.archive_ai_reply_to_records(db=db, user_id=user_id, thread_id=thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return result


@router.delete("/{thread_id}/archive-ai-reply", response_model=MailThreadArchiveResponse)
def unarchive_ai_reply_from_records(
    thread_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadArchiveResponse:
    try:
        result = mail_thread_service.unarchive_ai_reply_from_records(db=db, user_id=user_id, thread_id=thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return result


@router.patch("/{thread_id}/complete", response_model=MailThreadResponse)
def complete_mail_thread(
    thread_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    mail_thread_service: MailThreadService = Depends(get_mail_thread_service),
) -> MailThreadResponse:
    thread = mail_thread_service.complete_thread(db=db, user_id=user_id, thread_id=thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread
