from app.adapters.llm_client import LLMClient
from app.adapters.planner_actor_adapter import build_style_summary, normalize_persona_name
from app.core.config import Settings
from app.prompts.planner_prompt import build_planner_system_prompt
from app.utils.json_parse import safe_json_parse
from typing import Any

RISK_KEYWORDS = ("自杀", "轻生", "不想活", "活着很累", "伤害自己", "自残", "扛不住了")
GENERATION_PLAN_ALIASES = (
    "generation_plan",
    "reply_outline",
    "outline",
    "plan",
    "writing_plan",
    "response_plan",
)
OMITTED_PLANNER_FIELDS = {
    "story_plan",
    "surface_issue",
    "positive_motive",
    "persona_strategy",
    "response_focus",
    "action_strategy",
    "sample_words",
    "must_include",
    "must_avoid",
}


class PlannerService:
    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client

    async def create_plan(
        self,
        user_input: str,
        persona_name: str,
        safety_context: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        persona_name = normalize_persona_name(persona_name)
        style_summary = build_style_summary(persona_name)

        if self.settings.effective_planner_mode == "mock":
            return self._mock_plan(user_input=user_input, style_summary=style_summary, safety_context=safety_context or {})

        raw = await self.llm_client.complete_api(
            provider="gpt",
            model=self.settings.planner_model,
            messages=[
                {"role": "system", "content": build_planner_system_prompt(style_summary, safety_context)},
                {"role": "user", "content": f"【用户来信】\n{user_input}"},
            ],
            temperature=0.2,
            timeout=self.settings.planner_timeout_seconds,
        )
        parsed = safe_json_parse(raw)
        if not parsed:
            raise ValueError("Planner did not return valid JSON")

        self._normalize_formulation(parsed, safety_context or {})
        for field in OMITTED_PLANNER_FIELDS:
            parsed.pop(field, None)
        parsed["raw"] = raw
        parsed["style_summary"] = style_summary
        return parsed

    def _mock_plan(
        self,
        user_input: str,
        style_summary: dict[str, str],
        safety_context: dict[str, Any],
    ) -> dict[str, object]:
        return {
            "surface_problems": ["用户正在承受持续压力，希望有人帮助自己看清当前困扰。"],
            "possible_core_concern": "用户可能在持续压力下出现掌控感下降，但目前信息不足，不能直接替用户定义动机。",
            "supporting_evidence": [{"quote": user_input[:120], "supports": "用户主动来信求助，说明当前困扰已经需要外部支持。"}],
            "uncertainties": ["当前压力持续了多久，以及对睡眠、学习和生活的影响程度尚不明确。"],
            "generation_plan": "围绕当前困扰展开，先作具体承接，再帮助用户看清冲突结构，最后提供保留选择空间的行动方向。",
            "avoid_conclusions": ["不要直接断言用户的真实动机，也不要把困难归因为不够努力。"],
            "advice_principles": ["提供一个足够小的开始方向和多个可选路径，不规定精确脚本。"],
            "safety_assessment": safety_context,
            "style_summary": style_summary,
            "raw": "",
        }

    def _normalize_formulation(
        self,
        planner_output: dict[str, object],
        safety_context: dict[str, Any],
    ) -> None:
        self._normalize_generation_plan(planner_output)
        planner_output["surface_problems"] = self._string_list(
            planner_output.get("surface_problems") or planner_output.get("intention")
        )
        planner_output["possible_core_concern"] = str(
            planner_output.get("possible_core_concern") or planner_output.get("core_issue") or ""
        ).strip()
        planner_output["supporting_evidence"] = self._evidence_list(planner_output.get("supporting_evidence"))
        planner_output["uncertainties"] = self._string_list(planner_output.get("uncertainties"))
        planner_output["generation_plan"] = str(
            planner_output.get("generation_plan") or planner_output.get("reply_focus") or ""
        ).strip()
        planner_output["avoid_conclusions"] = self._string_list(
            planner_output.get("avoid_conclusions") or planner_output.get("wrong_but_easy_answer")
        )
        planner_output["advice_principles"] = self._string_list(
            planner_output.get("advice_principles") or planner_output.get("value_guidance")
        )
        planner_output["safety_assessment"] = self._normalize_safety_assessment(
            planner_output.get("safety_assessment"),
            safety_context,
        )
        planner_output["risk_assessment"] = self._render_risk_assessment(
            planner_output["safety_assessment"]
        )

        for legacy_key in (
            "intention",
            "core_issue",
            "reply_focus",
            "wrong_but_easy_answer",
            "value_guidance",
        ):
            planner_output.pop(legacy_key, None)

    def _render_risk_assessment(self, value: object) -> str:
        assessment = value if isinstance(value, dict) else {}
        reasoning = str(assessment.get("reasoning") or "").strip()
        risk_level = str(assessment.get("risk_level") or "NONE").strip()
        risk_types = self._string_list(assessment.get("risk_types"))
        avoid_in_reply = self._string_list(assessment.get("avoid_in_reply"))
        protective_suggestions = self._string_list(assessment.get("protective_suggestions"))
        handoff = str(assessment.get("handoff") or "none").strip().lower()

        if reasoning:
            risk_text = reasoning
        elif risk_types:
            risk_text = f"风险等级 {risk_level}，识别到：{'、'.join(risk_types)}。"
        elif risk_level == "NONE":
            risk_text = "未识别到明确安全风险。"
        else:
            risk_text = f"风险等级为 {risk_level}。"

        handling: list[str] = []
        if avoid_in_reply:
            handling.append(f"避免：{'；'.join(avoid_in_reply)}")
        if protective_suggestions:
            handling.append(f"可加入：{'；'.join(protective_suggestions)}")
        if handoff in {"review", "priority", "urgent"}:
            handoff_labels = {"review": "建议人工复核", "priority": "建议优先转人工", "urgent": "需要立即转人工"}
            handling.append(handoff_labels[handoff])

        if not handling:
            handling.append("回信按一般支持性原则处理，避免夸大或替用户下结论。")
        return f"风险识别：{risk_text}\n处理方式：{'；'.join(handling)}"

    def _string_list(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value is None:
            return []
        rendered = str(value).strip()
        return [rendered] if rendered else []

    def _evidence_list(self, value: object) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        result: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            quote = str(item.get("quote") or "").strip()
            supports = str(item.get("supports") or "").strip()
            if quote or supports:
                result.append({"quote": quote, "supports": supports})
        return result

    def _normalize_safety_assessment(
        self,
        value: object,
        fallback: dict[str, Any],
    ) -> dict[str, object]:
        assessment = value if isinstance(value, dict) else {}
        risk_level = str(assessment.get("risk_level") or fallback.get("risk_level") or "NONE").upper()
        if risk_level not in {"NONE", "LOW", "MEDIUM", "HIGH", "CRISIS"}:
            risk_level = str(fallback.get("risk_level") or "NONE").upper()
        handoff = str(assessment.get("handoff") or fallback.get("handoff") or "none").lower()
        if handoff not in {"none", "review", "priority", "urgent"}:
            handoff = str(fallback.get("handoff") or "none").lower()

        def list_value(key: str) -> list[str]:
            source = assessment.get(key) if key in assessment else fallback.get(key)
            return self._string_list(source)

        return {
            "risk_level": risk_level,
            "risk_types": list_value("risk_types"),
            "evidence": list_value("evidence"),
            "reasoning": str(assessment.get("reasoning") or fallback.get("reasoning") or "").strip(),
            "uncertainties": list_value("uncertainties"),
            "avoid_in_reply": list_value("avoid_in_reply"),
            "protective_suggestions": list_value("protective_suggestions"),
            "handoff": handoff,
        }

    def _normalize_generation_plan(self, planner_output: dict[str, object]) -> None:
        current_value = self._render_generation_plan_value(planner_output.get("generation_plan"))
        if current_value:
            planner_output["generation_plan"] = current_value
            return

        for alias in GENERATION_PLAN_ALIASES:
            alias_value = self._render_generation_plan_value(planner_output.get(alias))
            if alias_value:
                planner_output["generation_plan"] = alias_value
                return

    def _render_generation_plan_value(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return "\n".join(str(item).strip() for item in value if str(item).strip())
        if isinstance(value, dict):
            preferred_keys = (
                "core_focus",
                "empathy_entry",
                "analysis_direction",
                "action_direction",
                "risk_handling",
                "ending",
            )
            lines: list[str] = []
            used_keys: set[str] = set()
            for key in preferred_keys:
                if key in value:
                    rendered = self._render_generation_plan_value(value.get(key))
                    if rendered:
                        lines.append(rendered)
                        used_keys.add(key)
            for key, nested_value in value.items():
                if key in used_keys:
                    continue
                rendered = self._render_generation_plan_value(nested_value)
                if rendered:
                    lines.append(rendered)
            return "\n".join(lines).strip()
        return str(value).strip()
