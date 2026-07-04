from __future__ import annotations

from typing import Any

STYLE_AXES_DEF: dict[str, dict[str, str]] = {
    "narrative": {
        "无案例": "不讲故事，把篇幅留给问题本质、认知拆解和自然嵌入的下一步。",
        "轻案例": "只使用一句到一小段贴近学生生活的例子，帮助来信者感到被理解。",
        "启发故事": "故事或例子必须带来新视角，不能复刻来信烦恼；故事后必须明确迁移到来信者处境。",
    },
    "advice": {
        "概念启发": "不机械列点，用生活化语言帮助来信者重新理解处境与自我价值。",
        "结构引导": "把判断框架讲清楚，再给 1 到 2 个自然可做的下一步；不要写成策略清单。",
        "微步实操": "给出当晚、明天或下一次类似场景中可以直接尝试的小动作、话术或边界设置。",
    },
    "empathy": {
        "理性克制": "简洁承接情绪，建议占全文 10%-15%，避免长篇复述，把重点放在看清问题与给出抓手。",
        "温和接纳": "温暖承接情绪，建议占全文约 20%，同时保持清醒，不把回信写成单纯安慰。",
        "深度镜像": "替来信者说出没有明说的委屈、害怕、正面动机和未被看见的努力，建议占全文 25%-30%，之后必须转入分析与行动。",
    },
    "cognitive": {
        "顺应跟随": "先接住来信者视角，再温和打开一个更稳、更有希望的理解角度。",
        "认知解绑": "指出把暂时困境等同于自我否定、把外界评价等同于个人价值等卡点。",
        "价值澄清": "帮助来信者看见选择、边界、学习、人际或亲子沟通背后的价值取向与长期影响。",
    },
}

PERSONAS: dict[str, dict[str, str]] = {
    "温暖倾听者": {
        "narrative": "轻案例",
        "advice": "概念启发",
        "empathy": "深度镜像",
        "cognitive": "顺应跟随",
        "empathy_ratio": "25%-30%",
        "analysis_ratio": "30%-35%",
        "action_ratio": "25%-30%",
        "target_length": "1200字以上",
    },
    "理性破局教练": {
        "narrative": "无案例",
        "advice": "结构引导",
        "empathy": "理性克制",
        "cognitive": "认知解绑",
        "empathy_ratio": "15%-20%",
        "analysis_ratio": "40%-45%",
        "action_ratio": "30%-35%",
        "target_length": "800-950字之间",
    },
    "启发故事导师": {
        "narrative": "启发故事",
        "advice": "微步实操",
        "empathy": "温和接纳",
        "cognitive": "价值澄清",
        "empathy_ratio": "15%-20%",
        "analysis_ratio": "25%-30%",
        "action_ratio": "30%-35%",
        "target_length": "1300 字以上",
    },
}

PERSONA_ALIASES = {
    "理性教练": "理性破局教练",
    "犀利破局者": "理性破局教练",
    "故事导师": "启发故事导师",
    "哲理长者": "启发故事导师",
}

DEFAULT_PERSONA = "温暖倾听者"


def normalize_persona_name(persona_name: str | None) -> str:
    if not persona_name:
        return DEFAULT_PERSONA
    if persona_name in PERSONAS:
        return persona_name
    return PERSONA_ALIASES.get(persona_name, DEFAULT_PERSONA)


def get_persona_style_config(persona_name: str) -> dict[str, str]:
    normalized = normalize_persona_name(persona_name)
    return PERSONAS[normalized]


def get_all_persona_names() -> list[str]:
    return list(PERSONAS.keys())


def build_style_summary(persona_name: str) -> dict[str, Any]:
    normalized = normalize_persona_name(persona_name)
    style_config = get_persona_style_config(normalized)

    return {
        "persona_name": normalized,
        "narrative": style_config["narrative"],
        "advice": style_config["advice"],
        "empathy": style_config["empathy"],
        "cognitive": style_config["cognitive"],
        "empathy_ratio": style_config["empathy_ratio"],
        "analysis_ratio": style_config["analysis_ratio"],
        "action_ratio": style_config["action_ratio"],
        "target_length": style_config["target_length"],
        "narrative_desc": STYLE_AXES_DEF["narrative"][style_config["narrative"]],
        "advice_desc": STYLE_AXES_DEF["advice"][style_config["advice"]],
        "empathy_desc": STYLE_AXES_DEF["empathy"][style_config["empathy"]],
        "cognitive_desc": STYLE_AXES_DEF["cognitive"][style_config["cognitive"]],
    }
