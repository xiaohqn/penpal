from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_record_service
from app.schemas.record import (
    ConsultationRecordResponse,
    ConsultationRecordSaveRequest,
    ConsultationRecordListResponse,
)
from app.services.record_service import RecordService

router = APIRouter(prefix="/records", tags=["records"])


@router.post(
    "",
    response_model=ConsultationRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_record(
    payload: ConsultationRecordSaveRequest,
    db: Session = Depends(get_db_session),
    record_service: RecordService = Depends(get_record_service),
) -> ConsultationRecordResponse:
    return record_service.create_record(db=db, payload=payload)


@router.get("", response_model=ConsultationRecordListResponse)
def list_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db_session),
    record_service: RecordService = Depends(get_record_service),
) -> ConsultationRecordListResponse:
    return record_service.list_records(db=db, page=page, page_size=page_size)


@router.get("/{record_id}", response_model=ConsultationRecordResponse)
def get_record(
    record_id: int,
    db: Session = Depends(get_db_session),
    record_service: RecordService = Depends(get_record_service),
) -> ConsultationRecordResponse:
    record = record_service.get_record(db=db, record_id=record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record
