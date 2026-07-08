from app.prompts.generator_prompt import build_generator_system_prompt
from app.prompts.planner_prompt import build_planner_system_prompt


STYLE_SUMMARY = {
    "persona_name": "温暖倾听者",
    "narrative": "低",
    "narrative_desc": "少叙事",
    "advice": "结构引导",
    "advice_desc": "自然给出建议",
    "empathy": "温和接纳",
    "empathy_desc": "温暖承接情绪",
    "cognitive": "轻度",
    "cognitive_desc": "轻量认知引导",
    "empathy_ratio": "20%",
    "analysis_ratio": "35%",
    "action_ratio": "45%",
    "target_length": "中等",
}


def test_generator_prompt_bans_generic_empathy_phrases():
    prompt = build_generator_system_prompt({}, STYLE_SUMMARY)

    assert "换谁都会这样" in prompt
    assert "换谁都会难受" in prompt
    assert "泛化式共情句" in prompt
    assert "贴着来信细节" in prompt


def test_planner_prompt_keeps_generic_empathy_out_of_plan():
    prompt = build_planner_system_prompt(STYLE_SUMMARY)

    assert "换谁都会这样" in prompt
    assert "换谁都会难受" in prompt
    assert "泛化共情句" in prompt
    assert "来信细节" in prompt
