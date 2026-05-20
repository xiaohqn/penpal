import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from plan import (  # type: ignore  # noqa: E402
    PERSONAS,
    STYLE_AXES_DEF,
    get_all_persona_names,
    get_persona_style_config,
)

DEFAULT_PERSONA = "温暖倾听者"


def normalize_persona_name(persona_name: str | None) -> str:
    if persona_name and persona_name in PERSONAS:
        return persona_name
    return DEFAULT_PERSONA


def build_style_summary(persona_name: str) -> dict[str, str]:
    normalized = normalize_persona_name(persona_name)
    style_config = get_persona_style_config(normalized)

    return {
        "persona_name": normalized,
        "narrative": style_config["narrative"],
        "advice": style_config["advice"],
        "empathy": style_config["empathy"],
        "cognitive": style_config["cognitive"],
        "narrative_desc": STYLE_AXES_DEF["narrative"][style_config["narrative"]],
        "advice_desc": STYLE_AXES_DEF["advice"][style_config["advice"]],
        "empathy_desc": STYLE_AXES_DEF["empathy"][style_config["empathy"]],
        "cognitive_desc": STYLE_AXES_DEF["cognitive"][style_config["cognitive"]],
    }


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
