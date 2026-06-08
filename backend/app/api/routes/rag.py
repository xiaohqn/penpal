from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_rag_service
from app.schemas.rag import RagSampleResponse, RagSearchRequest, RagSearchResponse
from app.services.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagSearchResponse)
def search_rag_samples(
    payload: RagSearchRequest,
    db: Session = Depends(get_db_session),
    rag_service: RagService = Depends(get_rag_service),
) -> RagSearchResponse:
    samples = rag_service.retrieve_samples(
        db=db,
        user_input=payload.user_input,
        planner_output=payload.planner_output,
        persona_name=payload.persona_name,
        limit=payload.limit,
    )
    return RagSearchResponse(
        items=[
            RagSampleResponse(
                id=sample.id,
                source=sample.source,
                score=round(sample.score, 3),
                selected_persona_name=sample.selected_persona_name,
                user_input=sample.user_input,
                expert_response=sample.expert_response,
                expert_annotation=sample.expert_annotation,
                sample_tags=sample.sample_tags,
                planner_labels=sample.planner_labels,
            )
            for sample in samples
        ]
    )
