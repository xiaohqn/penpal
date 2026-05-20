from pydantic import BaseModel


class PersonaItem(BaseModel):
    name: str
    blurb: str
    style_config: dict[str, str]
    raw_config: dict[str, str]


class PersonaCatalogResponse(BaseModel):
    personas: list[PersonaItem]
    style_axes: dict[str, dict[str, str]]
