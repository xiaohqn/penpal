import asyncio
from collections.abc import AsyncIterator
from typing import Any

from app.adapters.planner_actor_adapter import build_style_summary, normalize_persona_name
from app.core.config import Settings
from app.core.sse import format_sse
from app.services.generator_service import GeneratorService
from app.services.planner_service import PlannerService


class OrchestrationService:
    def __init__(
        self,
        settings: Settings,
        planner_service: PlannerService,
        generator_service: GeneratorService,
    ):
        self.settings = settings
        self.planner_service = planner_service
        self.generator_service = generator_service

    async def stream_generation(
        self,
        user_input: str,
        persona_names: list[str],
        compare_sources: bool = False,
        source_mode: str = "auto",
    ) -> AsyncIterator[str]:
        ordered_personas: list[str] = []
        for persona_name in persona_names:
            normalized = normalize_persona_name(persona_name)
            if normalized not in ordered_personas:
                ordered_personas.append(normalized)

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        completed_by_draft_id: dict[str, dict[str, Any]] = {}
        generator_targets = self._build_generator_targets(compare_sources, source_mode)

        async def worker(persona_name: str, target: dict[str, str]) -> None:
            draft_id = self._build_draft_id(persona_name, target["source"])
            await queue.put(
                {
                    "event": "draft_started",
                    "draft_id": draft_id,
                    "persona_name": persona_name,
                    "source": target["source"],
                    "source_label": target["label"],
                }
            )
            try:
                planner_output = await self.planner_service.create_plan(user_input, persona_name)
                await queue.put(
                    {
                        "event": "planner_ready",
                        "draft_id": draft_id,
                        "persona_name": persona_name,
                        "source": target["source"],
                        "source_label": target["label"],
                        "planner_output": planner_output,
                    }
                )
                draft_result = await self.generator_service.generate_with_mode(
                    user_input=user_input,
                    planner_output=planner_output,
                    persona_name=persona_name,
                    mode=target["mode"],
                )
                full_response = draft_result["response"]
                async for chunk in self.generator_service.emit_chunks(full_response):
                    await queue.put(
                        {
                            "event": "draft_delta",
                            "draft_id": draft_id,
                            "persona_name": persona_name,
                            "source": target["source"],
                            "source_label": target["label"],
                            "delta": chunk,
                        }
                    )

                completed_by_draft_id[draft_id] = {
                    "draft_id": draft_id,
                    "persona_name": persona_name,
                    "source": target["source"],
                    "source_label": target["label"],
                    "style_config": build_style_summary(persona_name),
                    "planner_output": planner_output,
                    "response": full_response,
                    "raw_response": draft_result["raw"],
                }
                await queue.put(
                    {
                        "event": "draft_done",
                        "draft_id": draft_id,
                        "persona_name": persona_name,
                        "source": target["source"],
                        "source_label": target["label"],
                        "response": full_response,
                    }
                )
            except Exception as exc:
                await queue.put(
                    {
                        "event": "error",
                        "draft_id": draft_id,
                        "persona_name": persona_name,
                        "source": target["source"],
                        "source_label": target["label"],
                        "message": str(exc),
                    }
                )
            finally:
                await queue.put({"event": "__task_complete__"})

        tasks = [
            asyncio.create_task(worker(persona_name, target))
            for persona_name in ordered_personas
            for target in generator_targets
        ]

        yield format_sse(
            "job_started",
            {
                "event": "job_started",
                "persona_count": len(ordered_personas),
                "source_count": len(generator_targets),
                "persona_names": ordered_personas,
            },
        )

        done_count = 0
        while done_count < len(tasks):
            event = await queue.get()
            if event["event"] == "__task_complete__":
                done_count += 1
                continue
            yield format_sse(event["event"], event)

        await asyncio.gather(*tasks, return_exceptions=True)
        ordered_drafts = [
            completed_by_draft_id[self._build_draft_id(persona_name, target["source"])]
            for persona_name in ordered_personas
            for target in generator_targets
            if self._build_draft_id(persona_name, target["source"]) in completed_by_draft_id
        ]
        yield format_sse(
            "job_done",
            {
                "event": "job_done",
                "drafts": ordered_drafts,
            },
        )

    async def generate_all(
        self,
        user_input: str,
        persona_names: list[str],
        compare_sources: bool = False,
        source_mode: str = "auto",
    ) -> list[dict[str, Any]]:
        ordered_personas: list[str] = []
        for persona_name in persona_names:
            normalized = normalize_persona_name(persona_name)
            if normalized not in ordered_personas:
                ordered_personas.append(normalized)

        generator_targets = self._build_generator_targets(compare_sources, source_mode)

        async def worker(persona_name: str, target: dict[str, str]) -> dict[str, Any] | None:
            try:
                planner_output = await self.planner_service.create_plan(user_input, persona_name)
                draft_result = await self.generator_service.generate_with_mode(
                    user_input=user_input,
                    planner_output=planner_output,
                    persona_name=persona_name,
                    mode=target["mode"],
                )
                return {
                    "draft_id": self._build_draft_id(persona_name, target["source"]),
                    "persona_name": persona_name,
                    "source": target["source"],
                    "source_label": target["label"],
                    "style_config": build_style_summary(persona_name),
                    "planner_output": planner_output,
                    "response": draft_result["response"],
                    "raw_response": draft_result["raw"],
                }
            except Exception:
                return None

        results = await asyncio.gather(
            *(worker(persona_name, target) for persona_name in ordered_personas for target in generator_targets)
        )
        return [item for item in results if item is not None]

    def _build_generator_targets(self, compare_sources: bool, source_mode: str) -> list[dict[str, str]]:
        normalized_mode = source_mode.strip().lower()
        if normalized_mode == "compare":
            compare_sources = True

        if normalized_mode == "api":
            return [{"mode": "api", "source": "api", "label": "API 模型"}]
        if normalized_mode == "vllm":
            return [{"mode": "vllm", "source": "vllm", "label": "本地 vLLM"}]

        if compare_sources:
            targets: list[dict[str, str]] = []
            if self.settings.doubao_api_key:
                targets.append({"mode": "api", "source": "api", "label": "API 模型"})
            if self.settings.vllm_model_name:
                targets.append({"mode": "vllm", "source": "vllm", "label": "本地 vLLM"})
            if targets:
                return targets
        mode = self.settings.effective_generator_mode
        if mode == "vllm":
            return [{"mode": "vllm", "source": "vllm", "label": "本地 vLLM"}]
        if mode == "local":
            return [{"mode": "local", "source": "local", "label": "本地模型"}]
        if mode == "api":
            return [{"mode": "api", "source": "api", "label": "API 模型"}]
        return [{"mode": "mock", "source": "mock", "label": "Mock"}]

    def _build_draft_id(self, persona_name: str, source: str) -> str:
        return f"{persona_name}::{source}"
