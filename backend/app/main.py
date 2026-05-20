from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.llm_client import LLMClient
from app.api.routes.generation import router as generation_router
from app.api.routes.health import router as health_router
from app.api.routes.personas import router as personas_router
from app.api.routes.records import router as records_router
from app.api.routes.batch import router as batch_router
from app.core.config import Settings, get_settings
from app.db.session import build_engine, build_session_factory, init_db
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.generator_service import GeneratorService
from app.services.orchestration_service import OrchestrationService
from app.services.persona_service import PersonaService
from app.services.planner_service import PlannerService
from app.services.record_service import RecordService


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
    orchestration_service = OrchestrationService(
        settings=settings,
        planner_service=planner_service,
        generator_service=generator_service,
    )
    record_service = RecordService()
    excel_service = ExcelService()
    batch_session_service = BatchSessionService()

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_maker = session_maker
    app.state.llm_client = llm_client
    app.state.persona_service = persona_service
    app.state.planner_service = planner_service
    app.state.generator_service = generator_service
    app.state.orchestration_service = orchestration_service
    app.state.record_service = record_service
    app.state.excel_service = excel_service
    app.state.batch_session_service = batch_session_service

    api_router = APIRouter(prefix=settings.api_v1_prefix)
    api_router.include_router(health_router)
    api_router.include_router(personas_router)
    api_router.include_router(generation_router)
    api_router.include_router(records_router)
    api_router.include_router(batch_router)
    app.include_router(api_router)

    return app


app = create_app()
