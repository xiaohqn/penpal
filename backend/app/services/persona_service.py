from app.adapters.planner_actor_adapter import STYLE_AXES_DEF, build_persona_catalog
from app.schemas.persona import PersonaCatalogResponse


class PersonaService:
    def get_catalog(self) -> PersonaCatalogResponse:
        return PersonaCatalogResponse(
            personas=build_persona_catalog(),
            style_axes=STYLE_AXES_DEF,
        )
