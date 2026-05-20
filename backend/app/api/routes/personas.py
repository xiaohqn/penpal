from fastapi import APIRouter, Depends

from app.api.deps import get_persona_service
from app.schemas.persona import PersonaCatalogResponse
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=PersonaCatalogResponse)
def list_personas(
    persona_service: PersonaService = Depends(get_persona_service),
) -> PersonaCatalogResponse:
    return persona_service.get_catalog()
