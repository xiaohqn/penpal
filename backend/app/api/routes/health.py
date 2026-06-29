from fastapi import APIRouter, Depends, Request

from app.api.deps import get_settings
from app.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    rag_service = getattr(request.app.state, "rag_service", None)
    return {
        "status": "ok",
        "version": settings.app_version,
        "mock_llm": settings.use_mock_llm,
        "compare_model_outputs": settings.compare_model_outputs,
        "planner_mode": settings.effective_planner_mode,
        "generator_mode": settings.effective_generator_mode,
        "local_generator_configured": bool(settings.resolve_local_generator_model_path()),
        "vllm_configured": bool(settings.vllm_model_name),
        "counselor_features_enabled": settings.counselor_features_enabled,
        "rag_seed": rag_service.seed_status() if rag_service is not None else {},
    }
