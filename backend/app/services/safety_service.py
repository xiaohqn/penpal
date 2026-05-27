"""
输入：
- 用户提交的来信文本、风险检测结果、针对安全回复的专家批注，以及安全回复历史库中的 few-shot 样本。
- 全局配置、LLM 客户端、数据库会话工厂和安全回复记录服务。
输出：
- 返回风险标签、风险原因、是否安全，以及在高风险场景下生成或重生成的安全回复、高亮片段和高亮来源。
作用：
- 这个服务负责串起“风险检测 -> 历史安全样本检索 -> 安全回复生成 / 重生成”整条链路，
  是安全回复 RAG / few-shot 能力的主编排入口。
"""
from sqlalchemy.orm import sessionmaker

from app.adapters.llm_client import LLMClient
from app.core.config import Settings
from app.schemas.safety import SafetyCheckResponse, SafetyResponseCandidate
from app.services.find_unsafe import detect_single_letter
from app.services.safe_reply_highlight_service import SafeReplyHighlightService
from app.services.safe_reply import generate_single_safe_reply
from app.services.safety_record_service import SafetyRecordService

RISK_LABELS = {
    0: "安全",
    1: "自杀倾向",
    2: "针对他人的暴力或伤害倾向",
    3: "非自杀性自伤行为",
    4: "严重的物质滥用",
    5: "严重的进食障碍",
    6: "疑似精神病性症状",
    7: "卷入高危活动或畸形关系",
}

RISK_KEYWORDS = {
    1: ("自杀", "轻生", "不想活", "活着没意义", "想消失"),
    2: ("杀了", "捅死", "报复", "伤害他", "伤害她", "让他们付出代价"),
    3: ("自残", "割腕", "割自己", "伤害自己", "用疼痛", "流血时"),
    4: ("酗酒", "喝酒喝到断片", "吸毒", "药物上瘾", "离了它我撑不下去"),
    5: ("不吃饭", "暴食", "催吐", "只喝水", "卡路里"),
    6: ("幻听", "有人在命令我", "被监控", "特殊电波", "墙里有东西"),
    7: ("他打我", "离不开他", "危险驾驶", "赌博", "违法交易", "必须听从"),
}


class SafetyModeUnavailableError(ValueError):
    """
    输入：
    - 当前安全检测请求希望使用的来源模式，以及服务端现有的安全链路配置状态。
    输出：
    - 抛出一个可被 API 层转换为前端友好错误提示的异常。
    作用：
    - 专门表达“用户选择了某种安全来源模式，但当前后端并未接入”的场景，
      避免安全链路无提示地回退到另一种模式。
    """


class SafetyService:
    """
    输入：
    - settings：全局运行配置。
    - llm_client：统一注入的 LLM 客户端。
    - session_maker：数据库会话工厂，用于在安全检测流程里读取历史安全样本。
    - safety_record_service：安全回复记录服务，用于按修正后风险标签检索 few-shot 样本。
    - safe_reply_highlight_service：安全回复高亮提取服务，用于从完整安全回复中找出需要重点高亮的安全部分。
    输出：
    - 构造一个可复用的安全检测与安全回复服务实例。
    作用：
    - 把风险识别、few-shot 检索、安全回复生成和高亮提取依赖集中注入，供 API 层直接调用。
    """

    def __init__(
        self,
        settings: Settings,
        llm_client: LLMClient,
        session_maker: sessionmaker,
        safety_record_service: SafetyRecordService,
        safe_reply_highlight_service: SafeReplyHighlightService,
    ):
        self.settings = settings
        self.llm_client = llm_client
        self.session_maker = session_maker
        self.safety_record_service = safety_record_service
        self.safe_reply_highlight_service = safe_reply_highlight_service

    async def regenerate_safe_response_from_annotations(
        self,
        *,
        user_input: str,
        risk_codes: list[int],
        corrected_risk_labels: list[str],
        risk_reason: str,
        current_response: str,
        source_annotations: list[dict[str, str | int]],
        expert_annotation: str,
        source: str,
    ) -> SafetyResponseCandidate:
        """
        输入：
        - user_input：原始高风险来信正文，仍然是安全回复重生成的主问题。
        - risk_codes：原始安全检测得到的风险编号，用于在人工标签无法完整映射时兜底。
        - corrected_risk_labels：人工修正后的风险标签，用于 few-shot 检索并尽量贴合人工判断。
        - risk_reason：当前保留的风险原因说明。
        - current_response：当前正在被专家批注的安全回复正文。
        - source_annotations：专家在当前安全回复里高亮出的片段与逐条批注。
        - expert_annotation：专家对整条安全回复的总体修改说明。
        - source：当前安全回复候选来源，决定这次重生成走 API、本地模型还是 mock。
        输出：
        - 返回一份新的安全回复候选，包含重生成后的正文、意图和重新抽取的高亮片段。
        作用：
        - 专门承接“安全回复专家批注再生成”场景，避免前端把已生成回复与专家意见重新送回安全检测入口造成误判。
        """

        normalized_source = source.strip().lower()
        if normalized_source == "local":
            local_model_path = self.settings.resolve_local_generator_model_path()
            if local_model_path is None or self.settings.effective_safety_mode != "local":
                raise SafetyModeUnavailableError(
                    "当前选择的是本地安全回复，但安全链路未接入本地安全模型。"
                )
        if normalized_source == "api" and not self.settings.doubao_api_key:
            raise SafetyModeUnavailableError(
                "当前选择的是 API 安全回复，但安全链路未配置 DOUBAO_API_KEY。"
            )
        if normalized_source == "mock" and self.settings.effective_safety_mode != "mock":
            raise SafetyModeUnavailableError(
                "当前选择的是 Mock 安全回复，但服务端并未启用 mock 安全链路。"
            )

        annotation_block = self._build_annotation_block(source_annotations)
        if not annotation_block and not expert_annotation.strip():
            raise ValueError("请先添加至少一条高亮批注，或填写专家总体说明后再重生成。")

        effective_labels = corrected_risk_labels or self._labels_from_codes(risk_codes)
        regenerated_risk_codes = self._derive_risk_codes_from_labels(
            corrected_risk_labels=effective_labels,
            fallback_risk_codes=risk_codes,
        )
        augmented_user_input = self._build_regenerate_user_input(
            user_input=user_input,
            current_response=current_response,
            annotation_block=annotation_block,
            expert_annotation=expert_annotation,
        )
        few_shot_examples = self._load_few_shot_examples(effective_labels)

        return await self._build_safe_response_candidate(
            user_input=augmented_user_input,
            risk_codes=regenerated_risk_codes,
            risk_reason=risk_reason,
            few_shot_examples=few_shot_examples,
            source=normalized_source,
            source_label=self._build_safety_source_label(normalized_source),
            if_local=normalized_source == "local",
            allow_mock=normalized_source == "mock",
        )

    async def check_user_input(
        self,
        user_input: str,
        *,
        source_mode: str = "auto",
    ) -> SafetyCheckResponse:
        """
        输入：
        - user_input：待检测并生成安全回复的用户来信正文。
        - source_mode：前端当前选中的来源模式，用于让安全链路感知用户是否显式选择了 `vllm`。
        输出：
        - 返回完整的安全检测结果；如果识别为高风险，还会附带生成后的安全回复、
          从安全回复中抽出的高亮片段，以及高亮片段是 `llm` 还是 `fallback` 提取的来源信息。
        作用：
        - 统一完成风险检测、历史安全样本召回和最终安全回复生成，是 `/safety/check`
          接口的核心业务逻辑。
        """

        normalized_source_mode = source_mode.strip().lower()
        if normalized_source_mode == "compare":
            return await self._check_user_input_with_compare(user_input)

        # 安全检测、安全回复和安全高亮需要保持相同的路由策略；
        # 这里先统一算出安全链路自己的实际模式，再派生出是否走本地模型，避免三段逻辑各自判断后出现不一致。
        safety_mode = self._resolve_safety_mode(normalized_source_mode)
        use_local_safety_model = safety_mode == "local"

        if safety_mode == "mock":
            codes, reason = self._mock_detect(user_input)
        else:
            detection_result = detect_single_letter(user_input, if_local=use_local_safety_model)
            codes = detection_result.get("risk_codes") or [0]
            reason = detection_result.get("reason") or ""

        labels = [RISK_LABELS.get(code, f"未知风险({code})") for code in codes]
        is_safe = codes == [0]

        if is_safe:
            return SafetyCheckResponse(
                risk_codes=[0],
                risk_labels=[RISK_LABELS[0]],
                reason=reason or "未检测到明显严重心理安全风险。",
                is_safe=True,
                safe_highlight_segments=[],
                safe_highlight_source=None,
            )

        few_shot_examples = self._load_few_shot_examples(labels)
        primary_candidate = await self._build_safe_response_candidate(
            user_input=user_input,
            risk_codes=codes,
            risk_reason=reason,
            few_shot_examples=few_shot_examples,
            source=safety_mode,
            source_label=self._build_safety_source_label(safety_mode),
            if_local=use_local_safety_model,
            allow_mock=True,
        )

        return SafetyCheckResponse(
            risk_codes=codes,
            risk_labels=labels,
            reason=reason or "检测到需要额外关注的心理安全风险。",
            is_safe=False,
            intent=primary_candidate.intent,
            safe_response=primary_candidate.safe_response,
            safe_highlight_segments=primary_candidate.safe_highlight_segments,
            safe_highlight_source=primary_candidate.safe_highlight_source,
            safe_response_candidates=[primary_candidate],
        )

    def _resolve_safety_mode(self, source_mode: str) -> str:
        """
        输入：
        - source_mode：前端当前选中的来源模式。
        输出：
        - 返回这次安全检测请求真正应该采用的安全链路模式。
        作用：
        - 当用户在工作台顶部显式点了 `vLLM` 时，安全链路不应该悄悄继续走 API；
          如果当前并未接入本地安全模型，就应该直接返回明确提示。
        """

        normalized_source_mode = source_mode.strip().lower()
        effective_safety_mode = self.settings.effective_safety_mode

        if normalized_source_mode == "vllm":
            local_model_path = self.settings.resolve_local_generator_model_path()
            if effective_safety_mode != "local" or local_model_path is None:
                raise SafetyModeUnavailableError(
                    "当前已选择 vLLM，但安全链路未接入本地安全模型。请将 SAFETY_MODE 设为 local 并配置本地模型，或切回 API。"
                )
            return "local"

        if normalized_source_mode == "api":
            if not self.settings.doubao_api_key:
                raise SafetyModeUnavailableError(
                    "当前已选择 API，但安全链路未配置 DOUBAO_API_KEY。"
                )
            return "api"

        # `auto` 会沿用安全链路自己的显式模式配置；`compare` 已经在上游单独分流，不会走到这里。
        return effective_safety_mode

    async def _check_user_input_with_compare(self, user_input: str) -> SafetyCheckResponse:
        """
        输入：
        - user_input：待检测并生成安全回复的用户来信正文。
        输出：
        - 返回一份带有多候选安全回复的安全检测结果；若当前无法同时提供 API 与本地候选，会直接抛出明确错误。
        作用：
        - 为安全链路提供“对比模式”编排，让前端可以像普通草稿那样切换查看 API 与本地安全模型生成的安全回复差异。
        """

        if not self.settings.doubao_api_key:
            raise SafetyModeUnavailableError(
                "当前已选择对比模式，但安全链路未配置 DOUBAO_API_KEY，无法生成 API 安全回复。"
            )

        local_model_path = self.settings.resolve_local_generator_model_path()
        if local_model_path is None:
            raise SafetyModeUnavailableError(
                "当前已选择对比模式，但安全链路未接入本地安全模型。请配置本地模型后再比较。"
            )

        detection_result = detect_single_letter(user_input, if_local=False)
        codes = detection_result.get("risk_codes") or [0]
        reason = detection_result.get("reason") or ""
        labels = [RISK_LABELS.get(code, f"未知风险({code})") for code in codes]
        is_safe = codes == [0]

        if is_safe:
            return SafetyCheckResponse(
                risk_codes=[0],
                risk_labels=[RISK_LABELS[0]],
                reason=reason or "未检测到明显严重心理安全风险。",
                is_safe=True,
                safe_highlight_segments=[],
                safe_highlight_source=None,
                safe_response_candidates=[],
            )

        few_shot_examples = self._load_few_shot_examples(labels)
        api_candidate = await self._build_safe_response_candidate(
            user_input=user_input,
            risk_codes=codes,
            risk_reason=reason,
            few_shot_examples=few_shot_examples,
            source="api",
            source_label="API 安全回复",
            if_local=False,
            allow_mock=False,
        )
        local_candidate = await self._build_safe_response_candidate(
            user_input=user_input,
            risk_codes=codes,
            risk_reason=reason,
            few_shot_examples=few_shot_examples,
            source="local",
            source_label="本地安全模型安全回复",
            if_local=True,
            allow_mock=False,
        )

        return SafetyCheckResponse(
            risk_codes=codes,
            risk_labels=labels,
            reason=reason or "检测到需要额外关注的心理安全风险。",
            is_safe=False,
            intent=api_candidate.intent,
            safe_response=api_candidate.safe_response,
            safe_highlight_segments=api_candidate.safe_highlight_segments,
            safe_highlight_source=api_candidate.safe_highlight_source,
            safe_response_candidates=[api_candidate, local_candidate],
        )

    async def _build_safe_response_candidate(
        self,
        *,
        user_input: str,
        risk_codes: list[int],
        risk_reason: str,
        few_shot_examples: list[dict[str, str | int | list[str]]],
        source: str,
        source_label: str,
        if_local: bool,
        allow_mock: bool,
    ) -> SafetyResponseCandidate:
        """
        输入：
        - user_input：当前高风险来信内容。
        - risk_codes / risk_reason：本次风险检测输出，用于驱动安全回复生成。
        - few_shot_examples：按修正风险标签检索出的历史安全样本。
        - source / source_label：当前候选的内部来源标记与前端展示名称。
        - if_local：是否让该候选走本地安全模型。
        - allow_mock：是否允许当前候选继续沿用 `SAFETY_MODE=mock` 的本地演示逻辑。
        输出：
        - 返回单个安全回复候选对象，包含完整正文、意图摘要和专属高亮结果。
        作用：
        - 统一封装“生成候选回复 + 提取候选高亮”的重复逻辑，让单路模式和对比模式都复用同一份实现。
        """

        if allow_mock and self.settings.effective_safety_mode == "mock":
            intent, safe_response = self._mock_safe_reply(
                user_input,
                self._labels_from_codes(risk_codes),
                few_shot_examples,
            )
        else:
            try:
                reply_result = generate_single_safe_reply(
                    user_input,
                    risk_codes,
                    risk_reason,
                    few_shot_examples=few_shot_examples,
                    if_local=if_local,
                )
            except (ImportError, ModuleNotFoundError) as exc:
                if if_local:
                    raise SafetyModeUnavailableError(
                        "当前已选择对比模式，但本地安全模型依赖未安装或未接入。"
                    ) from exc
                raise
            intent = reply_result.get("intent") or None
            safe_response = reply_result.get("response") or None

        normalized_safe_response = (
            safe_response or "请尽快联系信任的大人、老师或专业支持，先把自己放在安全的位置。"
        )
        safe_highlight_segments, safe_highlight_source = await self.safe_reply_highlight_service.extract_highlight_segments(
            normalized_safe_response,
            if_local=if_local,
        )

        return SafetyResponseCandidate(
            source=source,
            source_label=source_label,
            intent=intent,
            safe_response=normalized_safe_response,
            safe_highlight_segments=safe_highlight_segments,
            safe_highlight_source=safe_highlight_source,
        )

    def _build_regenerate_user_input(
        self,
        *,
        user_input: str,
        current_response: str,
        annotation_block: str,
        expert_annotation: str,
    ) -> str:
        """
        输入：
        - user_input：原始高风险来信。
        - current_response：当前正在被专家审阅的安全回复。
        - annotation_block：逐条整理后的高亮批注文本。
        - expert_annotation：专家对整条回复的整体说明。
        输出：
        - 返回拼接完成后的增强提示词文本。
        作用：
        - 把“原始来信 + 当前安全回复 + 专家批注”压成一段模型可直接消费的上下文，
          让新回复真正针对原回复问题进行修正，而不是重新从零自由发挥。
        """

        augmented_user_input = user_input.strip()
        if current_response.strip():
            augmented_user_input += f"\n\n【当前安全回复】\n{current_response.strip()}"
        if annotation_block:
            augmented_user_input += (
                f"\n\n【专家对当前安全回复的高亮批注】\n{annotation_block}\n\n"
                "请基于上述安全回复进行重写和修正，优先处理这些被高亮的片段，同时继续保持安全边界、现实求助建议和共情承接。"
            )
        if expert_annotation.strip():
            augmented_user_input += f"\n\n【专家总体说明】\n{expert_annotation.strip()}"
        return augmented_user_input

    def _build_annotation_block(self, source_annotations: list[dict[str, str | int]]) -> str:
        """
        输入：
        - source_annotations：前端传来的结构化高亮批注列表。
        输出：
        - 返回适合直接写进提示词的逐条批注文本；没有有效内容时返回空字符串。
        作用：
        - 把前端的批注结构转成模型更容易理解的自然语言清单，同时跳过空白批注，减少噪声。
        """

        lines: list[str] = []
        for index, annotation in enumerate(source_annotations, start=1):
            quote = str(annotation.get("quote", "")).strip()
            note = str(annotation.get("note", "")).strip()
            if not quote and not note:
                continue
            lines.append(f"{index}. 回复片段：{quote or '未填写'}；专家批注：{note or '未填写'}")
        return "\n".join(lines)

    def _build_safety_source_label(self, safety_mode: str) -> str:
        """
        输入：
        - safety_mode：本次安全链路的实际模式标记。
        输出：
        - 返回面向前端展示的来源名称。
        作用：
        - 把后端内部使用的模式值转成更直观的展示文案，避免前端到处散落模式名映射。
        """

        if safety_mode == "local":
            return "本地安全模型安全回复"
        if safety_mode == "api":
            return "API 安全回复"
        return "Mock 安全回复"

    def _derive_risk_codes_from_labels(
        self,
        *,
        corrected_risk_labels: list[str],
        fallback_risk_codes: list[int],
    ) -> list[int]:
        """
        输入：
        - corrected_risk_labels：人工修正后的风险标签列表。
        - fallback_risk_codes：安全检测原始产出的风险编号列表。
        输出：
        - 返回尽量贴近人工标签的一组风险编号；如果标签无法映射，则回退到原始编号。
        作用：
        - 让安全回复重生成既能尊重人工修正，又不会因为出现自定义标签而丢掉生成阶段必须依赖的风险编号。
        """

        label_to_code = {label: code for code, label in RISK_LABELS.items() if code != 0}
        mapped_codes = [
            label_to_code[label]
            for label in corrected_risk_labels
            if label in label_to_code and label != RISK_LABELS[0]
        ]
        if mapped_codes:
            return list(dict.fromkeys(mapped_codes))

        fallback_non_safe_codes = [code for code in fallback_risk_codes if code != 0]
        return fallback_non_safe_codes or [1]

    def _labels_from_codes(self, risk_codes: list[int]) -> list[str]:
        """
        输入：
        - risk_codes：安全检测阶段产出的风险编号列表。
        输出：
        - 返回与这些编号对应的风险标签列表。
        作用：
        - 让 mock 安全回复和其他需要标签文案的分支复用同一份编号到名称的转换结果，避免多处重复映射。
        """

        return [RISK_LABELS.get(code, f"未知风险({code})") for code in risk_codes]

    def _load_few_shot_examples(self, corrected_risk_labels: list[str]) -> list[dict[str, str | int | list[str]]]:
        """
        输入：
        - corrected_risk_labels：当前高风险来信对应的风险标签列表。
        输出：
        - 返回少量基于 `corrected_risk_labels_json` 检索出来的 few-shot 样本字典列表。
        作用：
        - 把数据库服务层的检索结果转成生成层更容易消费的结构，并控制样本数量，
          避免安全回复提示词过长、风格污染过重。
        """

        with self.session_maker() as db:
            examples = self.safety_record_service.find_few_shot_examples_by_corrected_labels(
                db=db,
                corrected_risk_labels=corrected_risk_labels,
                limit=3,
            )

        return [
            {
                "record_id": example.record_id,
                "corrected_risk_labels": example.corrected_risk_labels,
                "user_input": example.user_input,
                "risk_reason": example.risk_reason,
                "expert_polished_response": example.expert_polished_response,
            }
            for example in examples
        ]

    def _mock_detect(self, user_input: str) -> tuple[list[int], str]:
        matched_codes: list[int] = []
        for code, keywords in RISK_KEYWORDS.items():
            if any(keyword in user_input for keyword in keywords):
                matched_codes.append(code)

        if not matched_codes:
            return [0], "未检测到明显严重心理安全风险。"

        labels = [RISK_LABELS[code] for code in matched_codes]
        return matched_codes, f"来信中出现了与{'、'.join(labels)}相关的明显风险信号，需要优先进行安全回应。"

    def _mock_safe_reply(
        self,
        user_input: str,
        risk_labels: list[str],
        few_shot_examples: list[dict[str, str | int | list[str]]],
    ) -> tuple[str, str]:
        """
        输入：
        - user_input：当前高风险来信内容。
        - risk_labels：当前识别出的风险标签。
        - few_shot_examples：按修正后风险标签检索出来的历史安全样本。
        输出：
        - 返回 mock 模式下的意图总结和安全回复文本。
        作用：
        - 在测试或离线开发场景中模拟真实安全回复流程，同时让 mock 结果也能反映
          few-shot 检索是否生效。
        """

        intent = "来信人正处在明显的情绪失衡和求助边缘，最需要被接住、被认真看见，并尽快连接现实支持。"
        response = (
            "你好。我很认真地看完了你的来信，也能感觉到你现在承受的压力已经不只是普通的难过，而是到了需要先把安全放在第一位的时候。"
            f"你提到的这些内容里，已经出现了与{ '、'.join(risk_labels) }相关的危险信号，这并不说明你有问题，而是说明你现在真的已经太辛苦了，"
            "辛苦到不适合再一个人硬扛。\n\n"
            "这时候最重要的事情，不是逼自己立刻想通，也不是继续一个人忍着，而是尽快联系你信任的大人、老师、家长，或者专业的心理老师、医生，"
            "把你现在的状态原原本本告诉他们，让现实中的支持尽快接住你。如果你已经有很强的冲动，请先离开危险环境，不要让自己单独待着。\n\n"
            "你愿意把这些话写出来，本身就说明你其实还在努力求生、也还在期待被理解。这份努力很重要。请先把今天的自己保护好，也把求助这件事往前推一步。"
        )
        if few_shot_examples:
            response += (
                "\n\n从过往相似风险来信的处理经验看，越是在最难熬的时候，越需要尽快让现实里"
                "值得信任的大人、老师或专业支持介入，而不是继续独自承受。"
            )
        return intent, response
