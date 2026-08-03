from dataclasses import dataclass, field
from typing import Any


RISK_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRISIS": 4}


@dataclass(frozen=True)
class SafetyAssessment:
    risk_level: str
    confidence: float
    categories: list[str]
    signals: list[str]
    reasoning: str
    uncertainties: list[str] = field(default_factory=list)
    avoid_in_reply: list[str] = field(default_factory=list)
    protective_suggestions: list[str] = field(default_factory=list)
    handoff: str = "none"

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "risk_types": self.categories,
            "evidence": self.signals,
            "reasoning": self.reasoning,
            "uncertainties": self.uncertainties,
            "avoid_in_reply": self.avoid_in_reply,
            "protective_suggestions": self.protective_suggestions,
            "handoff": self.handoff,
        }


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
        typed_patterns: list[tuple[str, tuple[str, ...], int, str]] = [
            ("self_harm_metaphor", ("不想醒来", "不愿醒来", "永远睡过去", "消失就好了", "撑不住了", "撑不下去"), 2, "出现隐性的自我伤害或消失表达"),
            ("family_violence", ("被家暴", "被虐待", "妈妈打我", "爸爸打我", "家长打我", "会打我", "揍我", "扇我", "踢我"), 2, "出现家庭暴力或身体伤害线索"),
            ("minor_protection", ("爸妈天天吵", "父母天天吵", "爸妈一直吵", "父母一直吵", "长期争吵", "不让我上学"), 1, "出现未成年人长期处于家庭冲突或权益受损的线索"),
            ("coercive_control", ("威胁我", "逼迫我", "强迫我", "控制我", "不让我出门", "不许我联系", "不让我联系"), 2, "出现威胁、胁迫或关系控制线索"),
            ("bullying_or_isolation", ("校园霸凌", "被霸凌", "被孤立", "一直孤立我", "传播谣言", "造谣"), 2, "出现霸凌、孤立或持续性关系伤害线索"),
            ("severe_emotional_exhaustion", ("长期失眠", "每天失眠", "整夜睡不着", "无法学习", "没法学习", "不能上学", "没法上学", "无法生活", "每天崩溃"), 2, "出现持续耗竭或学习生活功能受损线索"),
            ("runaway_or_missing", ("离家出走", "不想回家", "再也不回家", "准备离开家"), 2, "出现离家出走或失联风险线索"),
            ("stalking_or_real_world_threat", ("被跟踪", "跟踪我", "堵我", "要报复我", "威胁要打我"), 3, "出现跟踪、报复或现实人身安全威胁"),
            ("substance_or_medication", ("药物滥用", "乱吃药", "大量吃药"), 2, "出现药物使用风险线索"),
            ("psychosis_like_experience", ("幻听", "幻觉"), 2, "出现知觉异常线索"),
        ]
        medium_keywords = ["活着没意义", "绝望", "没有希望"]
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
        for category, keywords, weight, description in typed_patterns:
            matched = [keyword for keyword in keywords if keyword in lowered]
            if matched:
                score += weight
                categories.add(category)
                signals.append(f"{description}：{matched[0]}")
        for keyword in medium_keywords:
            if keyword in lowered:
                score += 2
                signals.append(f"出现中度风险线索：{keyword}")
                categories.add("severe_emotional_exhaustion")
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
        uncertainties, avoid_in_reply, protective_suggestions = self._guidance_for_categories(categories)
        if level == "CRISIS":
            handoff = "urgent"
        elif level == "HIGH" or "stalking_or_real_world_threat" in categories:
            handoff = "priority"
        elif level == "MEDIUM" or categories.intersection(
            {"family_violence", "minor_protection", "coercive_control", "bullying_or_isolation", "stalking_or_real_world_threat"}
        ):
            handoff = "review"
        else:
            handoff = "none"
        return SafetyAssessment(
            risk_level=level,
            confidence=confidence,
            categories=sorted(categories),
            signals=signals[:8],
            reasoning=reasoning,
            uncertainties=uncertainties,
            avoid_in_reply=avoid_in_reply,
            protective_suggestions=protective_suggestions,
            handoff=handoff,
        )

    def _guidance_for_categories(self, categories: set[str]) -> tuple[list[str], list[str], list[str]]:
        uncertainties: list[str] = []
        avoid: list[str] = []
        protective: list[str] = []

        if categories.intersection({"suicide", "self_harm", "self_harm_metaphor"}):
            uncertainties.extend(["是否有当前伤害自己的冲动、计划或可获得的方式", "此刻是否有人可以陪伴或提供现实支持"])
            avoid.extend(["不要把消失或不想醒来的表达只当作普通情绪低落", "不要保证痛苦一定很快过去"])
            protective.extend(["确认此刻是否安全以及是否有立即伤害自己的风险", "鼓励尽快联系可信任的人、专业支持或紧急服务"])
        if categories.intersection({"family_violence", "minor_protection"}):
            uncertainties.extend(["伤害或冲突是否正在发生、频率和严重程度如何", "来信者是否有安全的成年人或临时去处"])
            avoid.extend(["不要建议来信者独自与可能施暴者正面对抗", "不要淡化为普通亲子沟通问题"])
            protective.extend(["优先确认当前环境是否安全", "鼓励联系可信任成年人、老师、亲属或当地未成年人保护支持"])
        if categories.intersection({"coercive_control", "bullying_or_isolation", "stalking_or_real_world_threat"}):
            uncertainties.extend(["威胁是否持续、是否升级以及是否存在现实接触风险", "学校、家庭或其他现实支持是否已经知情"])
            avoid.extend(["不要把持续威胁简单解释为沟通误会", "不要建议独自见面或直接刺激威胁者"])
            protective.extend(["建议保存威胁、跟踪或霸凌证据", "鼓励尽快向可信任成年人、学校或现实安全支持求助"])
        if "severe_emotional_exhaustion" in categories:
            uncertainties.extend(["睡眠、进食、学习和日常生活受影响的持续时间与程度", "是否同时出现绝望或自我伤害念头"])
            avoid.extend(["不要只提供时间管理或提高效率建议", "不要把功能受损归因为不够努力"])
            protective.extend(["建议降低近期负荷并寻求可信任成年人或专业支持", "关注睡眠、进食和基本生活是否还能维持"])
        return self._dedupe(uncertainties), self._dedupe(avoid), self._dedupe(protective)

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


def max_risk_level(levels: list[str]) -> str:
    return max(levels or ["NONE"], key=lambda level: RISK_ORDER.get(level, 0))
