from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_orchestration_service
from app.schemas.generation import GenerationRequest
from app.services.orchestration_service import OrchestrationService

router = APIRouter(prefix="/generations", tags=["generations"])


@router.post("/stream")
async def stream_generation(
    payload: GenerationRequest,
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> StreamingResponse:
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
