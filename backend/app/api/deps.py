from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.batch_session_service import BatchSessionService
from app.services.auth_service import AuthService
from app.services.excel_service import ExcelService
from app.services.orchestration_service import OrchestrationService
from app.services.persona_service import PersonaService
from app.services.record_service import RecordService
from app.services.rag_service import RagService
from app.services.user_letter_service import UserLetterService
from app.services.mail_thread_service import MailThreadService
from app.services.safety_service import SafetyService
from app.services.workspace_task_service import WorkspaceTaskService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_maker = request.app.state.session_maker
    db = session_maker()
    try:
        yield db
    finally:
        db.close()


def get_session_maker(request: Request):
    return request.app.state.session_maker


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


def get_rag_service(request: Request) -> RagService:
    return request.app.state.rag_service


def get_user_letter_service(request: Request) -> UserLetterService:
    return request.app.state.user_letter_service


def get_mail_thread_service(request: Request) -> MailThreadService:
    return request.app.state.mail_thread_service


def get_safety_service(request: Request) -> SafetyService:
    return request.app.state.safety_service


def get_workspace_task_service(request: Request) -> WorkspaceTaskService:
    return request.app.state.workspace_task_service
