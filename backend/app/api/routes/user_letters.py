from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_counselor_id, get_user_id
from app.api.deps import get_db_session, get_user_letter_service
from app.schemas.user_letter import (
    CounselorReplyRequest,
    UserLetterCreateRequest,
    UserLetterListResponse,
    UserLetterResponse,
    UserLetterStatusUpdateRequest,
)
from app.services.user_letter_service import UserLetterService

router = APIRouter(prefix="/user-letters", tags=["user-letters"])


@router.post("", response_model=UserLetterResponse, status_code=status.HTTP_201_CREATED)
def create_user_letter(
    payload: UserLetterCreateRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    user_letter_service: UserLetterService = Depends(get_user_letter_service),
) -> UserLetterResponse:
    try:
        return user_letter_service.create_letter(db=db, user_id=user_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=UserLetterListResponse)
def list_user_letters(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    user_letter_service: UserLetterService = Depends(get_user_letter_service),
) -> UserLetterListResponse:
    return user_letter_service.list_letters(db=db, user_id=user_id)


@router.get("/assigned/mine", response_model=UserLetterListResponse)
def list_assigned_user_letters(
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    user_letter_service: UserLetterService = Depends(get_user_letter_service),
) -> UserLetterListResponse:
    return user_letter_service.list_assigned_letters(db=db, counselor_id=counselor_id)


@router.post("/assigned/{letter_id}/reply", response_model=UserLetterResponse)
def submit_assigned_user_letter_reply(
    letter_id: int,
    payload: CounselorReplyRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    user_letter_service: UserLetterService = Depends(get_user_letter_service),
) -> UserLetterResponse:
    letter = user_letter_service.submit_counselor_reply(
        db=db,
        counselor_id=counselor_id,
        letter_id=letter_id,
        reply_text=payload.reply_text,
    )
    if letter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned letter not found")
    return letter


@router.get("/{letter_id}", response_model=UserLetterResponse)
def get_user_letter(
    letter_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    user_letter_service: UserLetterService = Depends(get_user_letter_service),
) -> UserLetterResponse:
    letter = user_letter_service.get_letter(db=db, user_id=user_id, letter_id=letter_id)
    if letter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not found")
    return letter


@router.patch("/{letter_id}/status", response_model=UserLetterResponse)
def update_user_letter_status(
    letter_id: int,
    payload: UserLetterStatusUpdateRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db_session),
    user_letter_service: UserLetterService = Depends(get_user_letter_service),
) -> UserLetterResponse:
    letter = user_letter_service.update_status(
        db=db,
        user_id=user_id,
        letter_id=letter_id,
        status=payload.status,
    )
    if letter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not found")
    return letter
