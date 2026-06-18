from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_orchestration_service, get_settings
from app.core.config import Settings
from app.schemas.generation import GenerateFromPlanRequest, GenerationRequest
from app.services.orchestration_service import OrchestrationService

router = APIRouter(prefix="/generations", tags=["generations"])


@router.post("/stream")
async def stream_generation(
    payload: GenerationRequest,
    settings: Settings = Depends(get_settings),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> StreamingResponse:
    if payload.source_mode == "api" and (
        settings.effective_planner_mode != "api" or not settings.doubao_api_key
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "真实回信模型未配置。请设置 MOCK_LLM=false、PLANNER_MODE=api、"
                "GENERATOR_MODE=api、GPT_API_KEY 和 DOUBAO_API_KEY。"
            ),
        )
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        orchestration_service.stream_generation(
            user_input=payload.user_input,
            persona_names=payload.persona_names,
            compare_sources=payload.compare_sources,
            source_mode=payload.source_mode,
        ),
        media_type="text/event-stream",
        headers=headers,
    )


@router.post("/from-plan")
async def generate_from_plan(
    payload: GenerateFromPlanRequest,
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> dict:
    return await orchestration_service.generate_from_plan(
        user_input=payload.user_input,
        persona_name=payload.persona_name,
        planner_output=payload.planner_output,
        source_mode=payload.source_mode,
    )
