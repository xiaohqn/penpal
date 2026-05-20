from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "mock_llm": settings.use_mock_llm,
        "compare_model_outputs": settings.compare_model_outputs,
        "planner_mode": settings.effective_planner_mode,
        "generator_mode": settings.effective_generator_mode,
        "local_generator_configured": bool(settings.resolve_local_generator_model_path()),
        "vllm_configured": bool(settings.vllm_model_name),
    }
