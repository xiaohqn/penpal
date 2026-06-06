import asyncio

from app.adapters.llm_client import LLMClient
from app.core.config import Settings
from app.services.generator_service import GeneratorService
from app.services.orchestration_service import OrchestrationService
from app.services.planner_service import PlannerService


async def collect_stream(service: OrchestrationService):
    items = []
    async for chunk in service.stream_generation(
        user_input="我最近有些低落，但想试着往前走。",
        persona_names=["温暖倾听者", "启发故事导师", "理性破局教练"],
    ):
        items.append(chunk)
    return "".join(items)


def test_orchestration_stream_completes_for_multiple_personas():
    settings = Settings(mock_llm=True)
    llm_client = LLMClient(settings)
    planner_service = PlannerService(settings=settings, llm_client=llm_client)
    generator_service = GeneratorService(settings=settings, llm_client=llm_client)
    orchestration_service = OrchestrationService(
        settings=settings,
        planner_service=planner_service,
        generator_service=generator_service,
    )

    output = asyncio.run(collect_stream(orchestration_service))
    assert "event: draft_started" in output
    assert "event: job_done" in output
    assert "启发故事导师" in output
