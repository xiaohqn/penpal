from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.orchestration_service import OrchestrationService
from app.services.persona_service import PersonaService
from app.services.record_service import RecordService
from app.services.safety_record_service import SafetyRecordService
from app.services.safety_service import SafetyService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_maker = request.app.state.session_maker
    db = session_maker()
    try:
        yield db
    finally:
        db.close()


def get_persona_service(request: Request) -> PersonaService:
    return request.app.state.persona_service


def get_orchestration_service(request: Request) -> OrchestrationService:
    return request.app.state.orchestration_service


def get_record_service(request: Request) -> RecordService:
    return request.app.state.record_service


def get_excel_service(request: Request) -> ExcelService:
    return request.app.state.excel_service


def get_batch_session_service(request: Request) -> BatchSessionService:
    return request.app.state.batch_session_service


def get_safety_record_service(request: Request) -> SafetyRecordService:
    return request.app.state.safety_record_service


def get_safety_service(request: Request) -> SafetyService:
    return request.app.state.safety_service
