from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.llm_client import LLMClient
from app.api.routes.generation import router as generation_router
from app.api.routes.health import router as health_router
from app.api.routes.personas import router as personas_router
from app.api.routes.records import router as records_router
from app.api.routes.batch import router as batch_router
from app.api.routes.rag import router as rag_router
from app.api.routes.user_letters import router as user_letters_router
from app.api.routes.mail_threads import router as mail_threads_router
from app.api.routes.auth import router as auth_router
from app.api.routes.workspace_tasks import router as workspace_tasks_router
from app.api.routes.research import router as research_router
from app.core.config import Settings, get_settings
from app.db.session import build_engine, build_session_factory, init_db
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.generator_service import GeneratorService
from app.services.orchestration_service import OrchestrationService
from app.services.persona_service import PersonaService
from app.services.planner_service import PlannerService
from app.services.record_service import RecordService
from app.services.rag_service import RagService
from app.services.user_letter_service import UserLetterService
from app.services.mail_thread_service import MailThreadService
from app.services.safety_service import SafetyService
from app.services.auth_service import AuthService
from app.services.workspace_task_service import WorkspaceTaskService
from app.services.research_event_service import ResearchEventService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = build_engine(settings)
    session_maker = build_session_factory(engine)
    init_db(engine)

    llm_client = LLMClient(settings)
    persona_service = PersonaService()
    planner_service = PlannerService(settings=settings, llm_client=llm_client)
    generator_service = GeneratorService(settings=settings, llm_client=llm_client)
    rag_service = RagService(
        seed_path=settings.rag_seed_path,
        seed_enabled=settings.rag_seed_enabled,
    )
    safety_service = SafetyService()
    orchestration_service = OrchestrationService(
        settings=settings,
        planner_service=planner_service,
        generator_service=generator_service,
        rag_service=rag_service,
        session_maker=session_maker,
        safety_service=safety_service,
    )
    record_service = RecordService(rag_service=rag_service)
    excel_service = ExcelService()
    batch_session_service = BatchSessionService(rag_service=rag_service)
    user_letter_service = UserLetterService(settings=settings)
    mail_thread_service = MailThreadService(
        settings=settings,
        safety_service=safety_service,
        orchestration_service=orchestration_service,
        record_service=record_service,
    )
    auth_service = AuthService(settings=settings)
    workspace_task_service = WorkspaceTaskService()
    research_event_service = ResearchEventService()

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_maker = session_maker
    app.state.llm_client = llm_client
    app.state.persona_service = persona_service
    app.state.planner_service = planner_service
    app.state.generator_service = generator_service
    app.state.orchestration_service = orchestration_service
    app.state.rag_service = rag_service
    app.state.record_service = record_service
    app.state.excel_service = excel_service
    app.state.batch_session_service = batch_session_service
    app.state.user_letter_service = user_letter_service
    app.state.safety_service = safety_service
    app.state.mail_thread_service = mail_thread_service
    app.state.auth_service = auth_service
    app.state.workspace_task_service = workspace_task_service
    app.state.research_event_service = research_event_service

    api_router = APIRouter(prefix=settings.api_v1_prefix)
    api_router.include_router(health_router)
    api_router.include_router(personas_router)
    api_router.include_router(generation_router)
    api_router.include_router(records_router)
    api_router.include_router(batch_router)
    api_router.include_router(rag_router)
    api_router.include_router(user_letters_router)
    api_router.include_router(mail_threads_router)
    api_router.include_router(auth_router)
    api_router.include_router(workspace_tasks_router)
    api_router.include_router(research_router)
    app.include_router(api_router)

    return app


app = create_app()
