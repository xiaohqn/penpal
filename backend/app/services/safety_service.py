from dataclasses import dataclass


RISK_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRISIS": 4}


@dataclass(frozen=True)
class SafetyAssessment:
    risk_level: str
    confidence: float
    categories: list[str]
    signals: list[str]
    reasoning: str


class SafetyService:
    def assess_user_letter(self, content: str, previous_levels: list[str] | None = None) -> SafetyAssessment:
        return self._assess(content=content, previous_levels=previous_levels or [], target_type="user_letter")

    def assess_reply(self, content: str) -> SafetyAssessment:
        lowered = content.lower()
        dangerous_patterns = [
            ("结束这一切", "可能将自杀描述为可接受选择", "suicide"),
            ("不如去死", "含有鼓励死亡或伤害的表达", "suicide"),
            ("你可以自杀", "直接鼓励自杀", "suicide"),
            ("割腕", "提供或强化自伤方式", "self_harm"),
            ("多吃点药", "可能提供危险药物建议", "substance"),
        ]
        signals: list[str] = []
        categories: set[str] = set()
        for keyword, signal, category in dangerous_patterns:
            if keyword in lowered:
                signals.append(signal)
                categories.add(category)
        if signals:
            return SafetyAssessment(
                risk_level="HIGH",
                confidence=0.86,
                categories=sorted(categories),
                signals=signals,
                reasoning="回复中出现可能鼓励自伤、自杀或危险行为的表达，需要拦截或改写。",
            )
        return SafetyAssessment(
            risk_level="NONE",
            confidence=0.62,
            categories=[],
            signals=[],
            reasoning="未发现明显鼓励自伤、自杀、诊断替代或危险建议的表达。",
        )

    def crisis_reply(self, counselor_available: bool = True) -> str:
        handoff = (
            "这封信会优先交给人工咨询师继续接住你。"
            if counselor_available
            else "我会先用更稳妥的方式回应你，但它不能替代现实中的紧急支持。"
        )
        return (
            "我认真看见了你现在的痛苦。你愿意把这些告诉我，很重要。\n\n"
            "如果你此刻有立即伤害自己的风险，或已经准备了具体方式，请现在先不要独处。"
            "请立刻联系当地紧急服务，或马上联系身边可信赖的人陪在你身边。\n\n"
            "在中国大陆，你可以拨打 120 或 110 寻求紧急帮助；如果你在其他地区，请联系当地紧急电话。"
            f"{handoff}"
        )

    def safe_fallback_reply(self, counselor_available: bool = True) -> str:
        handoff = (
            "为了更稳妥地回应你，这封信会优先交给人工咨询师。"
            if counselor_available
            else "为了更稳妥地回应你，我会先给出安全提醒；这不能替代现实中的专业支持。"
        )
        return (
            "我认真读完了你的来信。你现在承受的痛苦值得被认真对待。\n\n"
            f"{handoff}"
            "如果你此刻有伤害自己的冲动，请先联系身边可信赖的人，或寻求当地紧急帮助。"
        )

    def _assess(self, content: str, previous_levels: list[str], target_type: str) -> SafetyAssessment:
        lowered = content.lower()
        categories: set[str] = set()
        signals: list[str] = []
        score = 0
        has_crisis_signal = False

        crisis_keywords = [
            "今晚准备",
            "已经准备好了",
            "买好了药",
            "准备跳",
            "遗书",
            "结束生命",
            "不想活了今晚",
        ]
        high_keywords = [
            "自杀",
            "想死",
            "不想活",
            "伤害自己",
            "自残",
            "割腕",
            "轻生",
        ]
        medium_keywords = [
            "活着没意义",
            "撑不下去",
            "绝望",
            "没有希望",
            "长期失眠",
            "被家暴",
            "被虐待",
            "校园霸凌",
            "药物滥用",
            "幻听",
            "幻觉",
        ]
        low_keywords = ["焦虑", "抑郁", "崩溃", "孤独", "寂寞", "失眠", "难受"]

        for keyword in crisis_keywords:
            if keyword in lowered:
                has_crisis_signal = True
                score += 6
                signals.append(f"出现立即风险线索：{keyword}")
                categories.add("suicide")
        for keyword in high_keywords:
            if keyword in lowered:
                score += 4
                signals.append(f"出现自伤/自杀相关表达：{keyword}")
                categories.add("suicide" if keyword in {"自杀", "想死", "不想活", "轻生"} else "self_harm")
        for keyword in medium_keywords:
            if keyword in lowered:
                score += 2
                signals.append(f"出现中度风险线索：{keyword}")
                if keyword in {"被家暴", "被虐待"}:
                    categories.add("abuse")
                elif keyword == "校园霸凌":
                    categories.add("bullying")
                elif keyword == "药物滥用":
                    categories.add("substance")
                elif keyword in {"幻听", "幻觉"}:
                    categories.add("psychosis")
                else:
                    categories.add("depression")
        for keyword in low_keywords:
            if keyword in lowered:
                score += 1
                signals.append(f"出现情绪困扰表达：{keyword}")
                categories.add("emotional_distress")

        if previous_levels and any(level in {"HIGH", "CRISIS"} for level in previous_levels[-3:]) and score >= 2:
            score += 2
            signals.append("近期历史中已有高风险记录，当前表达仍有明显痛苦，风险趋势需关注")
            categories.add("risk_trend")

        if has_crisis_signal:
            level = "CRISIS"
        elif score >= 4:
            level = "HIGH"
        elif score >= 2:
            level = "MEDIUM"
        elif score >= 1:
            level = "LOW"
        else:
            level = "NONE"

        confidence = min(0.95, 0.52 + score * 0.07)
        reasoning = "；".join(signals[:5]) if signals else "未发现明显危机或高风险线索。"
        return SafetyAssessment(
            risk_level=level,
            confidence=confidence,
            categories=sorted(categories),
            signals=signals[:8],
            reasoning=reasoning,
        )


def max_risk_level(levels: list[str]) -> str:
    return max(levels or ["NONE"], key=lambda level: RISK_ORDER.get(level, 0))
