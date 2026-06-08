"""
输入：
- `Settings` 配置对象，包含数据库、CORS、RAG 种子和 LLM 等运行参数。
输出：
- 初始化完成的 FastAPI 应用实例，以及挂载到 `app.state` 上的数据库连接与各类服务对象。
作用：
- 作为后端应用装配入口，把主分支新增的 RAG/Planner 能力与当前分支的安全回复工作流一起注册到同一个应用中。
"""
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.llm_client import LLMClient
from app.api.routes.batch import router as batch_router
from app.api.routes.generation import router as generation_router
from app.api.routes.health import router as health_router
from app.api.routes.personas import router as personas_router
from app.api.routes.rag import router as rag_router
from app.api.routes.records import router as records_router
from app.api.routes.safety import router as safety_router
from app.api.routes.safety_records import router as safety_records_router
from app.core.config import Settings, get_settings
from app.db.session import build_engine, build_session_factory, init_db
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.generator_service import GeneratorService
from app.services.orchestration_service import OrchestrationService
from app.services.persona_service import PersonaService
from app.services.planner_service import PlannerService
from app.services.rag_service import RagService
from app.services.record_service import RecordService
from app.services.safe_reply_highlight_service import SafeReplyHighlightService
from app.services.safety_record_service import SafetyRecordService
from app.services.safety_service import SafetyService


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    输入：
    - 可选的 `settings`；未传入时会从环境变量与默认配置里加载。
    输出：
    - 返回已经注册数据库、服务实例与全部 API 路由的 FastAPI 应用。
    作用：
    - 集中完成应用装配，确保普通工作流、批量任务、RAG 和安全回复模块共享同一套底层资源。
    """
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
    orchestration_service = OrchestrationService(
        settings=settings,
        planner_service=planner_service,
        generator_service=generator_service,
        rag_service=rag_service,
        session_maker=session_maker,
    )
    record_service = RecordService(rag_service=rag_service)
    excel_service = ExcelService()
    batch_session_service = BatchSessionService(rag_service=rag_service)
    safety_record_service = SafetyRecordService()
    safe_reply_highlight_service = SafeReplyHighlightService(settings=settings)
    safety_service = SafetyService(
        settings=settings,
        llm_client=llm_client,
        session_maker=session_maker,
        safety_record_service=safety_record_service,
        safe_reply_highlight_service=safe_reply_highlight_service,
    )

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
    app.state.safety_record_service = safety_record_service
    app.state.safe_reply_highlight_service = safe_reply_highlight_service
    app.state.safety_service = safety_service

    api_router = APIRouter(prefix=settings.api_v1_prefix)
    api_router.include_router(health_router)
    api_router.include_router(personas_router)
    api_router.include_router(generation_router)
    api_router.include_router(records_router)
    api_router.include_router(batch_router)
    api_router.include_router(safety_router)
    api_router.include_router(safety_records_router)
    api_router.include_router(rag_router)
    app.include_router(api_router)

    return app


app = create_app()
