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
            "intention": "用户正在承受持续情绪压力，希望被理解，也希望有人帮自己看清困局并找到下一步。",
            "surface_issue": "来信者描述了学习、人际、家庭或情绪上的具体困扰。",
            "core_issue": "真正需要处理的是压力之下的自我价值感受损、掌控感下降，以及不知道如何把求助和行动落到具体场景。",
            "positive_motive": "来信者愿意写信，本身说明仍然想把生活过好，也在寻找一个更安全、更有效的办法。",
            "wrong_but_easy_answer": "不要只复述痛苦，也不要只给泛泛的学习计划、沟通建议或空洞鼓励。",
            "risk_assessment": risk_assessment,
            "value_guidance": "把问题和个人价值分开；遇到危险念头时，求助是保护自己，不是添麻烦。",
            "persona_strategy": (
                f"以{style_summary['persona_name']}的风格写作，突出"
                f"{style_summary['empathy']}式共情、{style_summary['advice']}式建议与"
                f"{style_summary['cognitive']}式认知介入。"
            ),
            "response_focus": "先看见来信者仍想把生活过好的正面动机，再把问题和自我价值分开，最后落到一个具体可尝试的小动作。",
            "story_plan": {
                "use_story": style_summary["narrative"] == "启发故事",
                "story_type": "真实人物故事/学生近似案例" if style_summary["narrative"] == "启发故事" else "不讲故事",
                "story_candidate": "选择一个能说明“暂时受挫不等于能力定型”的简短故事或类比" if style_summary["narrative"] == "启发故事" else "",
                "story_point": "故事必须帮助来信者看到另一种处理方式，而不是复述同样的烦恼。",
                "transfer_to_user": "把故事里的选择迁移成来信者当下可以尝试的一句话或一个动作。",
            },
            "action_strategy": [
                "先把最重的问题命名出来，而不是一次解决所有问题。",
                "找到一个可信任的大人、老师或同伴，用一句话开启求助。",
            ],
            "sample_words": [
                "我最近真的有点扛不住，想请你先听我说十分钟。",
                "我不是不想变好，我是现在不知道从哪一步开始。",
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
