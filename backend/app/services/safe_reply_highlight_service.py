"""
输入：
- 安全回复生成链路输出的 `safe_response` 纯文本。
- 全局配置，用于决定是否走 mock 模式以及使用哪一个豆包模型。
输出：
- 返回高亮片段列表，以及这些片段是由大模型提取还是由本地兜底规则提取的来源标记。
作用：
- 这个文件专门负责“从完整安全回复中二次识别安全部分”，让安全回复生成与高亮提取解耦，
  避免修改 `safe_reply.py` 的生成职责；同时复用与安全回复生成一致的豆包批量调用方式，
  让日志表现和调用习惯保持一致。
"""
import json
import re

from app.core.config import Settings
from clients.doubao_client import create_doubao_client

MAX_HIGHLIGHT_SEGMENTS = 5


class SafeReplyHighlightService:
    """
    输入：
    - settings：全局运行配置，决定是走 mock 逻辑还是调用真实豆包接口。
    输出：
    - 构造一个可复用的安全回复高亮提取服务实例。
    作用：
    - 把“调用模型识别安全句子”“解析模型结果”和“失败时兜底提取”集中到一个独立 service 中。
      这里特意复用与 `safe_reply.py` 相同的豆包客户端调用方式，便于调试时观察一致的批量生成日志。
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_highlight_segments(
        self,
        safe_response: str,
        *,
        if_local: bool = False,
        lora_path: str | None = None,
    ) -> tuple[list[str], str]:
        """
        输入：
        - safe_response：安全回复生成阶段产出的完整纯文本回复。
        - if_local：是否改用本地安全模型提取高亮；通常由上层根据主链路模式决定。
        - lora_path：本地模型可选的 LoRA 路径；当前仅在本地模式下透传给底层客户端。
        输出：
        - 返回一个二元组：第一个元素是 0 到 5 个需要前端高亮的安全片段，
          第二个元素是来源标记，取值为 `llm` 或 `fallback`。
        作用：
        - 在安全回复已经生成之后，再额外识别出“现实求助、脱离危险环境、自我保护”等关键安全建议，
          方便前端直接高亮展示，而不需要猜测文本中哪几句最重要。
        """

        normalized_response = safe_response.strip()
        if not normalized_response:
            return [], "fallback"

        # 高亮提取属于安全链路的一部分，所以这里应当遵循安全链路自己的模式判定，
        # 而不是沿用普通草稿主链路的 `use_mock_llm`。这样 `SAFETY_MODE=mock` 时，
        # 即使主链路仍在跑真实 API，这里也会稳定走本地兜底提取。
        if self.settings.effective_safety_mode == "mock":
            return self._fallback_extract_segments(normalized_response), "fallback"

        prompt = self._build_highlight_prompt(normalized_response)
        runtime_client = self._build_runtime_client(if_local=if_local)
        try:
            generation_kwargs = {
                "max_workers": 1,
                "temperature": 0.1,
                "extra_body": {"thinking": {"type": "disabled"}},
            }
            if lora_path:
                generation_kwargs["lora_path"] = lora_path

            completion = runtime_client.batch_generate(
                [[{"role": "user", "content": prompt}]],
                **generation_kwargs,
            )[0]
        except Exception:
            return self._fallback_extract_segments(normalized_response), "fallback"
        finally:
            runtime_client.close()

        parsed_segments = self._parse_highlight_response(completion, normalized_response)
        if parsed_segments:
            return parsed_segments, "llm"

        return self._fallback_extract_segments(normalized_response), "fallback"

    def _build_runtime_client(self, *, if_local: bool) -> object:
        """
        输入：
        - if_local：是否使用本地安全模型。
        输出：
        - 返回一个具备 `batch_generate` 和 `close` 方法的运行时客户端实例。
        作用：
        - 让高亮提取和安全回复生成共用同一套“远端豆包 / 本地 Qwen”切换方式，
          这样主链路切到本地后，高亮阶段不会意外回退到远端接口。
        """

        if if_local:
            from clients.qwen3_8b_client import create_qwen3_8b_client

            return create_qwen3_8b_client()

        return create_doubao_client(model=self.settings.generator_model)

    def _build_highlight_prompt(self, safe_response: str) -> str:
        """
        输入：
        - safe_response：待分析的安全回复正文。
        输出：
        - 返回发给大模型的提示词字符串。
        作用：
        - 明确要求模型只从原文中抽取安全部分，且以结构化 JSON 输出，降低前端无法定位原文片段的风险。
        """

        return f"""
你是一个“安全回复高亮标注器”。
我会给你一段已经写好的安全回复纯文本，请你只做一件事：找出其中最需要被高亮显示的安全部分。

判定标准：
1. 只选择与现实求助、自我保护、脱离危险环境、联系家长老师医生、停止伤害自己或他人等直接相关的句子或短语。
2. 不要选纯共情内容，不要选铺垫，不要改写，不要总结。
3. 你返回的每一项都必须是输入原文里真实存在的连续原文片段。
4. 最多返回 5 项，尽量短，但要保持语义完整。
5. 如果没有明确的安全建议，就返回空数组。

请严格输出 JSON，不要输出任何额外解释：
{{
  "safe_highlight_segments": ["片段1", "片段2"]
}}

待分析文本：
\"\"\"{safe_response}\"\"\"
""".strip()

    def _parse_highlight_response(self, raw_reply: str, safe_response: str) -> list[str]:
        """
        输入：
        - raw_reply：大模型返回的原始字符串。
        - safe_response：原始安全回复正文，用来校验片段是否真实存在。
        输出：
        - 返回经过解析、去重和原文校验后的高亮片段列表。
        作用：
        - 把不稳定的模型输出清洗成前端可直接消费的结果，并阻止不存在于原文中的改写句子混入高亮列表。
        """

        parsed_segments: list[str] = []
        normalized_reply = raw_reply.strip()
        if not normalized_reply:
            return []

        parsed_object: object | None = None
        try:
            parsed_object = json.loads(normalized_reply)
        except json.JSONDecodeError:
            if "{" in normalized_reply and "}" in normalized_reply:
                start = normalized_reply.find("{")
                end = normalized_reply.rfind("}") + 1
                try:
                    parsed_object = json.loads(normalized_reply[start:end])
                except json.JSONDecodeError:
                    parsed_object = None

        if isinstance(parsed_object, dict):
            candidate_segments = parsed_object.get("safe_highlight_segments", [])
            if isinstance(candidate_segments, list):
                parsed_segments = [str(item).strip() for item in candidate_segments if str(item).strip()]

        if not parsed_segments:
            match = re.search(r'"safe_highlight_segments"\s*:\s*\[(.*?)\]', normalized_reply, re.DOTALL)
            if match:
                parsed_segments = [
                    value.strip()
                    for value in re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))
                    if value.strip()
                ]

        return self._normalize_segments(safe_response, parsed_segments)

    def _fallback_extract_segments(self, safe_response: str) -> list[str]:
        """
        输入：
        - safe_response：完整安全回复正文。
        输出：
        - 返回基于关键词和句子切分兜底提取出的高亮片段。
        作用：
        - 在 mock 模式、模型不可用或模型输出异常时，仍然尽量稳定地找出需要重点提醒用户的安全建议。
        """

        sentence_candidates = self._split_sentences(safe_response)
        highlight_keywords = (
            "联系",
            "求助",
            "家长",
            "老师",
            "医生",
            "专业支持",
            "危险",
            "离开",
            "不要",
            "安全",
            "告诉他们",
            "单独待着",
            "医院",
            "报警",
            "热线",
            "信任的大人",
        )
        inferred_segments = [
            sentence for sentence in sentence_candidates if any(keyword in sentence for keyword in highlight_keywords)
        ]
        normalized_segments = self._normalize_segments(
            safe_response,
            inferred_segments[:MAX_HIGHLIGHT_SEGMENTS],
        )
        if normalized_segments:
            return normalized_segments

        return [sentence_candidates[-1]] if sentence_candidates else [safe_response]

    def _split_sentences(self, safe_response: str) -> list[str]:
        """
        输入：
        - safe_response：完整安全回复正文。
        输出：
        - 返回按中文标点和换行切开的句子列表。
        作用：
        - 为兜底提取提供更稳定的语义单元，避免把高亮片段切成过碎的半句。
        """

        collapsed_text = re.sub(r"\n+", "\n", safe_response.strip())
        sentence_candidates = re.split(r"(?<=[。！？!?])|\n+", collapsed_text)
        return [sentence.strip() for sentence in sentence_candidates if sentence.strip()]

    def _normalize_segments(self, safe_response: str, segments: list[str]) -> list[str]:
        """
        输入：
        - safe_response：完整安全回复正文。
        - segments：待清洗的候选高亮片段。
        输出：
        - 返回按原文顺序排列、去重且保证真实存在于正文中的片段列表。
        作用：
        - 确保前端后续做高亮时可以直接按原文定位，而不会出现重复片段、空片段或模型改写片段。
        """

        unique_segments: list[tuple[int, str]] = []
        seen_segments: set[str] = set()

        for segment in segments:
            cleaned_segment = segment.strip()
            if not cleaned_segment or cleaned_segment in seen_segments:
                continue

            match_index = safe_response.find(cleaned_segment)
            if match_index < 0:
                continue

            unique_segments.append((match_index, cleaned_segment))
            seen_segments.add(cleaned_segment)

        unique_segments.sort(key=lambda item: item[0])
        return [segment for _, segment in unique_segments[:MAX_HIGHLIGHT_SEGMENTS]]
