from app.adapters.persona_config import (
    PERSONAS,
    build_style_summary,
    get_all_persona_names,
    normalize_persona_name,
)


def build_persona_catalog() -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    for persona_name in get_all_persona_names():
        style_config = build_style_summary(persona_name)
        catalog.append(
            {
                "name": persona_name,
                "blurb": (
                    f"{style_config['narrative']} / {style_config['advice']} / "
                    f"{style_config['empathy']} / {style_config['cognitive']}"
                ),
                "style_config": style_config,
                "raw_config": PERSONAS[persona_name],
            }
        )
    return catalog
