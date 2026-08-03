import asyncio
from collections.abc import AsyncIterator
import logging
from time import perf_counter
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.adapters.planner_actor_adapter import build_style_summary, normalize_persona_name
from app.core.config import Settings
from app.core.sse import format_sse
from app.services.generator_service import GeneratorService
from app.services.planner_service import PlannerService
from app.services.rag_service import RagService
from app.services.safety_service import RISK_ORDER, SafetyService
from app.utils.style_guards import find_generic_empathy_phrase

RAG_REFERENCE_LIMIT = 2
logger = logging.getLogger("uvicorn.error")


class OrchestrationService:
    def __init__(
        self,
        settings: Settings,
        planner_service: PlannerService,
        generator_service: GeneratorService,
        rag_service: RagService | None = None,
        session_maker: sessionmaker | None = None,
        safety_service: SafetyService | None = None,
    ):
        self.settings = settings
        self.planner_service = planner_service
        self.generator_service = generator_service
        self.rag_service = rag_service or RagService()
        self.session_maker = session_maker
        self.safety_service = safety_service or SafetyService()

    async def stream_generation(
        self,
        user_input: str,
        persona_names: list[str],
        compare_sources: bool = False,
        source_mode: str = "auto",
        use_deep_thinking: bool = False,
    ) -> AsyncIterator[str]:
        ordered_personas: list[str] = []
        for persona_name in persona_names:
            normalized = normalize_persona_name(persona_name)
            if normalized not in ordered_personas:
                ordered_personas.append(normalized)

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        completed_by_draft_id: dict[str, dict[str, Any]] = {}
        generator_targets = self._build_generator_targets(compare_sources, source_mode)
        user_safety_context = self.safety_service.assess_user_letter(user_input).to_prompt_dict()

        async def worker(persona_name: str, target: dict[str, str]) -> None:
            worker_started_at = perf_counter()
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
                planner_started_at = perf_counter()
                planner_output = await self.planner_service.create_plan(
                    user_input,
                    persona_name,
                    safety_context=user_safety_context,
                )
                planner_ms = self._elapsed_ms(planner_started_at)
                rag_started_at = perf_counter()
                planner_output = self._attach_rag_references(
                    user_input=user_input,
                    persona_name=persona_name,
                    planner_output=planner_output,
                )
                rag_ms = self._elapsed_ms(rag_started_at)
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
                generator_started_at = perf_counter()
                streamed_chunks: list[str] = []
                first_token_ms: int | None = None
                async for chunk in self.generator_service.stream_with_mode(
                    user_input=user_input,
                    planner_output=planner_output,
                    persona_name=persona_name,
                    mode=target["mode"],
                    audience="counselor",
                    use_deep_thinking=use_deep_thinking,
                ):
                    if first_token_ms is None:
                        first_token_ms = self._elapsed_ms(generator_started_at)
                    streamed_chunks.append(chunk)
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
                raw_response = "".join(streamed_chunks)
                generator_ms = self._elapsed_ms(generator_started_at)
                safety_started_at = perf_counter()
                reviewed_draft = self._review_draft_response(raw_response)
                safety_ms = self._elapsed_ms(safety_started_at)
                full_response = reviewed_draft["response"]
                emit_ms = 0

                completed_by_draft_id[draft_id] = {
                    "draft_id": draft_id,
                    "persona_name": persona_name,
                    "source": target["source"],
                    "source_label": target["label"],
                    "style_config": build_style_summary(persona_name),
                    "planner_output": planner_output,
                    "response": full_response,
                    "raw_response": raw_response,
                    "safety_review": reviewed_draft["safety_review"],
                }
                await queue.put(
                    {
                        "event": "draft_done",
                        "draft_id": draft_id,
                        "persona_name": persona_name,
                        "source": target["source"],
                        "source_label": target["label"],
                        "response": full_response,
                        "safety_review": reviewed_draft["safety_review"],
                    }
                )
                self._log_generation_timing(
                    route="stream_generation",
                    persona_name=persona_name,
                    source=target["source"],
                    user_input=user_input,
                    planner_output=planner_output,
                    response=full_response,
                    planner_ms=planner_ms,
                    rag_ms=rag_ms,
                    generator_ms=generator_ms,
                    first_token_ms=first_token_ms or generator_ms,
                    safety_ms=safety_ms,
                    emit_ms=emit_ms,
                    total_ms=self._elapsed_ms(worker_started_at),
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
        audience: str = "counselor",
        use_deep_thinking: bool = False,
    ) -> list[dict[str, Any]]:
        ordered_personas: list[str] = []
        for persona_name in persona_names:
            normalized = normalize_persona_name(persona_name)
            if normalized not in ordered_personas:
                ordered_personas.append(normalized)

        generator_targets = self._build_generator_targets(compare_sources, source_mode)
        user_safety_context = self.safety_service.assess_user_letter(user_input).to_prompt_dict()

        async def worker(persona_name: str, target: dict[str, str]) -> dict[str, Any] | None:
            try:
                planner_output = await self.planner_service.create_plan(
                    user_input,
                    persona_name,
                    safety_context=user_safety_context,
                )
                planner_output = self._attach_rag_references(
                    user_input=user_input,
                    persona_name=persona_name,
                    planner_output=planner_output,
                )
                draft_result = await self.generator_service.generate_with_mode(
                    user_input=user_input,
                    planner_output=planner_output,
                    persona_name=persona_name,
                    mode=target["mode"],
                    audience=audience,
                    use_deep_thinking=use_deep_thinking,
                )
                reviewed_draft = self._review_draft_response(draft_result["response"])
                return {
                    "draft_id": self._build_draft_id(persona_name, target["source"]),
                    "persona_name": persona_name,
                    "source": target["source"],
                    "source_label": target["label"],
                    "style_config": build_style_summary(persona_name),
                    "planner_output": planner_output,
                    "response": reviewed_draft["response"],
                    "raw_response": draft_result["raw"],
                    "safety_review": reviewed_draft["safety_review"],
                }
            except Exception:
                return None

        results = await asyncio.gather(
            *(worker(persona_name, target) for persona_name in ordered_personas for target in generator_targets)
        )
        return [item for item in results if item is not None]

    async def generate_from_plan(
        self,
        user_input: str,
        persona_name: str,
        planner_output: dict[str, Any],
        source_mode: str = "auto",
        use_deep_thinking: bool = False,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        normalized_persona = normalize_persona_name(persona_name)
        target = self._build_generator_targets(False, source_mode)[0]
        planner_output = {
            key: value
            for key, value in planner_output.items()
            if key
            not in {
                "story_plan",
                "surface_issue",
                "positive_motive",
                "persona_strategy",
                "response_focus",
                "action_strategy",
                "sample_words",
            }
        }
        if not planner_output.get("safety_assessment"):
            planner_output["safety_assessment"] = self.safety_service.assess_user_letter(user_input).to_prompt_dict()
        rag_started_at = perf_counter()
        enriched_planner_output = self._attach_rag_references(
            user_input=user_input,
            persona_name=normalized_persona,
            planner_output=planner_output,
        )
        rag_ms = self._elapsed_ms(rag_started_at)
        generator_started_at = perf_counter()
        draft_result = await self.generator_service.generate_with_mode(
            user_input=user_input,
            planner_output=enriched_planner_output,
            persona_name=normalized_persona,
            mode=target["mode"],
            audience="counselor",
            use_deep_thinking=use_deep_thinking,
        )
        generator_ms = self._elapsed_ms(generator_started_at)
        safety_started_at = perf_counter()
        reviewed_draft = self._review_draft_response(draft_result["response"])
        safety_ms = self._elapsed_ms(safety_started_at)
        self._log_generation_timing(
            route="generate_from_plan",
            persona_name=normalized_persona,
            source=target["source"],
            user_input=user_input,
            planner_output=enriched_planner_output,
            response=reviewed_draft["response"],
            planner_ms=0,
            rag_ms=rag_ms,
            generator_ms=generator_ms,
            first_token_ms=generator_ms,
            safety_ms=safety_ms,
            emit_ms=0,
            total_ms=self._elapsed_ms(started_at),
        )
        return {
            "draft_id": self._build_draft_id(normalized_persona, target["source"]),
            "persona_name": normalized_persona,
            "source": target["source"],
            "source_label": target["label"],
            "style_config": build_style_summary(normalized_persona),
            "planner_output": enriched_planner_output,
            "response": reviewed_draft["response"],
            "raw_response": draft_result["raw"],
            "safety_review": reviewed_draft["safety_review"],
        }

    async def rewrite_annotations(
        self,
        current_response: str,
        annotations: list[dict[str, Any]],
        expert_annotation: str,
        persona_name: str,
        source_mode: str = "auto",
        use_deep_thinking: bool = False,
    ) -> dict[str, Any]:
        normalized_persona = normalize_persona_name(persona_name)
        target = self._build_generator_targets(False, source_mode)[0]
        if target["mode"] == "mock":
            revisions = []
            for annotation in annotations:
                original_text = str(annotation.get("quote") or current_response[int(annotation.get("start", 0)): int(annotation.get("end", 0))])
                note = str(annotation.get("note") or "").strip()
                revised_text = original_text if not note else f"{original_text}\n\n[Mock 改写提示] {note}"
                revisions.append(
                    {
                        "id": str(annotation.get("id", "")),
                        "revised_text": revised_text,
                    }
                )
            return {"revisions": revisions}

        annotation_lines = []
        for index, annotation in enumerate(annotations, start=1):
            annotation_lines.append(
                "\n".join(
                    [
                        f"{index}. id: {annotation.get('id', '')}",
                        f"原片段: {annotation.get('quote', '')}",
                        f"专家批注: {annotation.get('note', '')}",
                    ]
                )
            )
        prompt = "\n\n".join(annotation_lines)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是专业的心理回信局部润色助手。你只改写专家批注指出的片段，"
                    "不要重写全文，不要输出未被批注的内容。保持原回信的人称、语气、称呼和上下文连贯。"
                    "专家批注是硬性修改要求，不是参考意见；必须逐条落实到 revised_text 里。"
                    "除非批注明确要求“不改”，否则 revised_text 不得与原片段完全相同，也不得只替换一两个无关虚词。"
                    "如果批注要求补充建议、缩短、增强共情、减少复述或改变语气，你必须让替换文本出现可见变化。"
                    "禁止使用泛化式共情：不得用‘任谁、换谁、任何人、谁遇到这种事/情况’等泛指主体，"
                    "再接‘都会、都很难、都无法、都受不了、都会觉得、都会感到’等普遍化情绪判断。"
                    "例如‘换谁做都很憋屈’‘任谁都很难接受’都禁止；必须贴着当前来信的具体处境表达。"
                    "每个 revised_text 必须能直接替换原片段；长度尽量贴近批注要求，不能把完整回信塞进一个片段。"
                    "不要加编号、解释、Markdown 或引号。"
                    '只输出 JSON：{"revisions":[{"id":"批注 id","revised_text":"替换文本"}]}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"【当前完整回信，仅供理解上下文】\n{current_response}\n\n"
                    f"【专家总体说明】\n{expert_annotation or '暂无'}\n\n"
                    f"【需要局部改写的批注片段】\n{prompt}\n\n"
                    "请检查每条 revised_text：是否真正回应了对应专家批注；是否可以直接替换原片段；"
                    "是否避免了原样返回。只返回最终 JSON。"
                ),
            },
        ]
        from app.utils.json_parse import safe_json_parse

        raw = ""
        revisions: list[dict[str, Any]] | None = None
        for attempt in range(2):
            raw = await self.generator_service.generate_raw_with_mode(
                messages=messages,
                mode=target["mode"],
                temperature=0.35 if attempt == 0 else 0.2,
                audience="counselor",
                use_deep_thinking=use_deep_thinking,
            )
            parsed = safe_json_parse(raw) or {}
            candidate_revisions = parsed.get("revisions")
            if not isinstance(candidate_revisions, list):
                raise ValueError("局部批注改写没有返回有效 revisions")
            violation = next(
                (
                    phrase
                    for item in candidate_revisions
                    if isinstance(item, dict)
                    for phrase in [find_generic_empathy_phrase(str(item.get("revised_text", "")))]
                    if phrase
                ),
                None,
            )
            if not violation:
                revisions = candidate_revisions
                break
            messages = [
                *messages,
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"上次结果包含禁止的泛化共情表达“{violation}”。请重新输出全部 revisions，"
                        "删除这类‘任谁/换谁/任何人……都……’判断，改为只描述来信者的具体处境。"
                        "仍然只输出规定的 JSON。"
                    ),
                },
            ]
        if revisions is None:
            raise ValueError("局部批注改写连续出现泛化共情表达，请调整批注后重试")
        return {"revisions": revisions, "raw": raw}

    def _review_draft_response(self, response: str) -> dict[str, Any]:
        assessment = self.safety_service.assess_reply(response)
        blocked = RISK_ORDER.get(assessment.risk_level, 0) >= RISK_ORDER["HIGH"]
        final_response = self.safety_service.safe_fallback_reply() if blocked else response
        return {
            "response": final_response,
            "safety_review": {
                "risk_level": assessment.risk_level,
                "confidence": assessment.confidence,
                "categories": assessment.categories,
                "signals": assessment.signals,
                "reasoning": assessment.reasoning,
                "blocked": blocked,
                "replacement_used": blocked,
                "original_response": response if blocked else "",
            },
        }

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

    def _attach_rag_references(
        self,
        user_input: str,
        persona_name: str,
        planner_output: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.settings.rag_enabled:
            return planner_output
        if self.session_maker is None:
            return planner_output
        db = self.session_maker()
        try:
            samples = self.rag_service.retrieve_samples(
                db=db,
                user_input=user_input,
                planner_output=planner_output,
                persona_name=persona_name,
                limit=RAG_REFERENCE_LIMIT,
            )
        finally:
            db.close()
        if not samples:
            return planner_output
        return {
            **planner_output,
            "rag_references": [sample.to_prompt_block() for sample in samples],
        }

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)

    def _log_generation_timing(
        self,
        route: str,
        persona_name: str,
        source: str,
        user_input: str,
        planner_output: dict[str, Any],
        response: str,
        planner_ms: int,
        rag_ms: int,
        generator_ms: int,
        first_token_ms: int,
        safety_ms: int,
        emit_ms: int,
        total_ms: int,
    ) -> None:
        rag_count = len(planner_output.get("rag_references") or [])
        logger.info(
            "generation_timing route=%s persona=%s source=%s total_ms=%s planner_ms=%s rag_ms=%s "
            "generator_ms=%s first_token_ms=%s safety_ms=%s emit_ms=%s input_chars=%s planner_chars=%s rag_count=%s response_chars=%s",
            route,
            persona_name,
            source,
            total_ms,
            planner_ms,
            rag_ms,
            generator_ms,
            first_token_ms,
            safety_ms,
            emit_ms,
            len(user_input),
            len(str(planner_output)),
            rag_count,
            len(response),
        )
