from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    """
    输入：
    - 当前注入的全局配置对象。
    输出：
    - 返回一份适合前端或运维快速查看的健康检查结果，包含主要模式判定与关键配置是否存在。
    作用：
    - 让启动后排查配置问题更直接，尤其是在同时支持普通生成链路和独立安全链路的场景下。
    """

    return {
        "status": "ok",
        "version": settings.app_version,
        "mock_llm": settings.use_mock_llm,
        "compare_model_outputs": settings.compare_model_outputs,
        "planner_mode": settings.effective_planner_mode,
        "generator_mode": settings.effective_generator_mode,
        "safety_mode": settings.effective_safety_mode,
        "local_generator_configured": bool(settings.resolve_local_generator_model_path()),
        "vllm_configured": bool(settings.vllm_model_name),
    }
