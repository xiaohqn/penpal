from app.adapters.llm_client import LLMClient
from app.adapters.planner_actor_adapter import build_style_summary, normalize_persona_name
from app.core.config import Settings
from app.prompts.planner_prompt import build_planner_system_prompt
from app.utils.json_parse import safe_json_parse

RISK_KEYWORDS = ("自杀", "轻生", "不想活", "活着很累", "伤害自己", "自残", "扛不住了")


class PlannerService:
    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client

    async def create_plan(self, user_input: str, persona_name: str) -> dict[str, object]:
        persona_name = normalize_persona_name(persona_name)
        style_summary = build_style_summary(persona_name)

        if self.settings.effective_planner_mode == "mock":
            return self._mock_plan(user_input=user_input, style_summary=style_summary)

        raw = await self.llm_client.complete_api(
            provider="gpt",
            model=self.settings.planner_model,
            messages=[
                {"role": "system", "content": build_planner_system_prompt(style_summary)},
                {"role": "user", "content": f"【用户来信】\n{user_input}"},
            ],
            temperature=0.2,
        )
        parsed = safe_json_parse(raw)
        if not parsed:
            raise ValueError("Planner did not return valid JSON")

        parsed["raw"] = raw
        parsed["style_summary"] = style_summary
        return parsed

    def _mock_plan(self, user_input: str, style_summary: dict[str, str]) -> dict[str, object]:
        has_risk = any(keyword in user_input for keyword in RISK_KEYWORDS)
        risk_assessment = (
            "来信中出现较强的绝望或自伤风险信号，回信必须先表达重视，并明确鼓励尽快联系可信任的大人/老师/专业支持。"
            if has_risk
            else "未见明确自伤风险，但情绪负荷较重，需要在回信中提供稳定承接与清晰落地建议。"
        )

        return {
            "intent_analysis": (
                "用户正在承受持续情绪压力，希望被理解，同时需要一个更稳的解释框架和下一步行动抓手。"
            ),
            "risk_assessment": risk_assessment,
            "persona_strategy": (
                f"以{style_summary['persona_name']}的风格写作，突出"
                f"{style_summary['empathy']}式共情、{style_summary['advice']}式建议与"
                f"{style_summary['cognitive']}式认知介入。"
            ),
            "paragraph_plan": [
                "第一段先接住情绪，准确命名痛苦与疲惫感。",
                "第二段解释痛苦并不等于个人有问题，把处境和自我价值分开。",
                "第三段给出一到两个足够小、当天就能尝试的动作。",
                "第四段在结尾补充陪伴承诺；若有风险，则明确鼓励联系专业支持。",
            ],
            "must_include": [
                "明确回应用户并不是矫情或软弱",
                "至少提供一个可以立刻执行的小动作",
            ],
            "must_avoid": [
                "空洞鸡汤",
                "居高临下的说教",
                "过度诗化的比喻",
            ],
            "generation_plan": (
                "写成自然书信，不要像清单，也不要像评估报告。先陪伴，再解释，最后落到可以执行的小动作。"
            ),
            "style_summary": style_summary,
            "raw": "",
        }
