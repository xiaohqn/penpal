from app.core.config import Settings
from app.services.generator_service import GeneratorService


def build_service(**settings_overrides: object) -> GeneratorService:
    settings = Settings(_env_file=None, **settings_overrides)
    return GeneratorService(settings=settings, llm_client=None)  # type: ignore[arg-type]


def test_counselor_deep_thinking_is_explicitly_enabled() -> None:
    service = build_service(
        counselor_generator_extra_body={"thinking": {"type": "disabled"}, "custom": "kept"},
    )

    assert service._resolve_extra_body("counselor", True) == {
        "thinking": {"type": "enabled"},
        "custom": "kept",
    }


def test_counselor_deep_thinking_is_explicitly_disabled() -> None:
    service = build_service(
        counselor_generator_extra_body={"thinking": {"type": "enabled"}, "custom": "kept"},
    )

    assert service._resolve_extra_body("counselor", False) == {
        "thinking": {"type": "disabled"},
        "custom": "kept",
    }


def test_user_generator_configuration_is_not_controlled_by_counselor_switch() -> None:
    service = build_service(user_generator_extra_body={"thinking": {"type": "auto"}})

    assert service._resolve_extra_body("user", True) == {"thinking": {"type": "auto"}}
