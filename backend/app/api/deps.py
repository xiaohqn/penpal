"""
输入：
- FastAPI `Request` 对象，以及应用启动阶段挂载到 `app.state` 上的设置、数据库会话工厂与各类服务实例。
输出：
- 为路由层提供可被 `Depends(...)` 注入的 settings、数据库会话和业务服务对象。
作用：
- 统一封装 API 依赖注入入口，避免各个路由直接读取 `app.state`，同时把安全回复、RAG 和批量处理服务集中暴露给接口层。
"""
from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.batch_session_service import BatchSessionService
from app.services.excel_service import ExcelService
from app.services.orchestration_service import OrchestrationService
from app.services.persona_service import PersonaService
from app.services.rag_service import RagService
from app.services.record_service import RecordService
from app.services.safety_record_service import SafetyRecordService
from app.services.safety_service import SafetyService


def get_settings(request: Request) -> Settings:
    """返回当前应用共享的配置对象。"""
    return request.app.state.settings


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """按请求生命周期创建并回收数据库会话。"""
    session_maker = request.app.state.session_maker
    db = session_maker()
    try:
        yield db
    finally:
        db.close()


def get_persona_service(request: Request) -> PersonaService:
    """提供人格目录与人格配置相关服务。"""
    return request.app.state.persona_service


def get_orchestration_service(request: Request) -> OrchestrationService:
    """提供编排 Planner、Generator 与 RAG 的核心工作流服务。"""
    return request.app.state.orchestration_service


def get_record_service(request: Request) -> RecordService:
    """提供咨询记录读写与导出能力。"""
    return request.app.state.record_service


def get_excel_service(request: Request) -> ExcelService:
    """提供 Excel 导入导出能力。"""
    return request.app.state.excel_service


def get_batch_session_service(request: Request) -> BatchSessionService:
    """提供批量任务会话的持久化与版本管理能力。"""
    return request.app.state.batch_session_service


def get_safety_record_service(request: Request) -> SafetyRecordService:
    """提供安全回复记录的持久化能力。"""
    return request.app.state.safety_record_service


def get_safety_service(request: Request) -> SafetyService:
    """提供风险识别、安全回复生成与安全工作流编排能力。"""
    return request.app.state.safety_service


def get_rag_service(request: Request) -> RagService:
    """提供样本标签、RAG 辅助数据与检索相关能力。"""
    return request.app.state.rag_service
