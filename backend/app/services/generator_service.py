import asyncio
import re

from app.adapters.llm_client import LLMClient
from app.adapters.planner_actor_adapter import build_style_summary, normalize_persona_name
from app.core.config import Settings
from app.prompts.generator_prompt import build_generator_system_prompt
from app.utils.json_parse import parse_response_only

RISK_KEYWORDS = ("自杀", "轻生", "不想活", "活着很累", "伤害自己", "自残", "扛不住了")


class GeneratorService:
    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client

    async def generate(
        self,
        user_input: str,
        planner_output: dict[str, object],
        persona_name: str,
    ) -> dict[str, str]:
        return await self.generate_with_mode(
            user_input=user_input,
            planner_output=planner_output,
            persona_name=persona_name,
            mode=self.settings.effective_generator_mode,
        )

    async def generate_with_mode(
        self,
        user_input: str,
        planner_output: dict[str, object],
        persona_name: str,
        mode: str,
    ) -> dict[str, str]:
        persona_name = normalize_persona_name(persona_name)
        style_summary = build_style_summary(persona_name)
        generator_messages = [
            {
                "role": "system",
                "content": build_generator_system_prompt(planner_output, style_summary),
            },
            {
                "role": "user",
                "content": f"以下是用户来信，请根据 Planner 的计划写出最终回信：\n\n{user_input}",
            },
        ]

        if mode == "mock":
            response = self._mock_response(
                user_input=user_input,
                planner_output=planner_output,
                style_summary=style_summary,
            )
            return {"raw": "", "response": self._normalize_letter_format(response)}

        if mode == "local":
            local_model_path = self.settings.resolve_local_generator_model_path()
            if local_model_path is None:
                raise ValueError("LOCAL_MODEL_PATH or LOCAL_GENERATOR_MODEL_PATH is not configured")

            raw = await self.llm_client.complete_local(
                model_path=local_model_path,
                messages=generator_messages,
                temperature=0.55,
                max_new_tokens=self.settings.local_generator_max_new_tokens,
            )
        elif mode == "vllm":
            if not self.settings.vllm_model_name:
                raise ValueError("VLLM_MODEL_NAME is not configured")
            raw = await self.llm_client.complete_api(
                provider="vllm",
                model=self.settings.vllm_model_name,
                messages=generator_messages,
                temperature=0.55,
                timeout=self.settings.generator_timeout_seconds,
            )
        else:
            raw = await self.llm_client.complete_api(
                provider="doubao",
                model=self.settings.generator_model,
                messages=generator_messages,
                temperature=0.55,
                timeout=self.settings.generator_timeout_seconds,
            )
        response, _ = parse_response_only(raw)
        return {"raw": raw, "response": self._normalize_letter_format(response)}

    async def generate_raw_with_mode(
        self,
        messages: list[dict[str, str]],
        mode: str,
        temperature: float = 0.55,
    ) -> str:
        if mode == "local":
            local_model_path = self.settings.resolve_local_generator_model_path()
            if local_model_path is None:
                raise ValueError("LOCAL_MODEL_PATH or LOCAL_GENERATOR_MODEL_PATH is not configured")
            return await self.llm_client.complete_local(
                model_path=local_model_path,
                messages=messages,
                temperature=temperature,
                max_new_tokens=self.settings.local_generator_max_new_tokens,
            )
        if mode == "vllm":
            if not self.settings.vllm_model_name:
                raise ValueError("VLLM_MODEL_NAME is not configured")
            return await self.llm_client.complete_api(
                provider="vllm",
                model=self.settings.vllm_model_name,
                messages=messages,
                temperature=temperature,
                timeout=self.settings.generator_timeout_seconds,
            )
        return await self.llm_client.complete_api(
            provider="doubao",
            model=self.settings.generator_model,
            messages=messages,
            temperature=temperature,
            timeout=self.settings.generator_timeout_seconds,
        )

    def split_text(self, text: str) -> list[str]:
        chunk_size = max(1, self.settings.stream_chunk_size)
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)] or [""]

    async def emit_chunks(self, text: str):
        for chunk in self.split_text(text):
            yield chunk
            if self.settings.stream_chunk_delay_ms > 0:
                await asyncio.sleep(self.settings.stream_chunk_delay_ms / 1000)

    def _normalize_letter_format(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return cleaned
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        paragraphs = [paragraph.strip() for paragraph in cleaned.split("\n\n") if paragraph.strip()]
        if len(paragraphs) >= 4:
            return "\n\n".join(paragraphs)

        sentences = [item.strip() for item in re.split(r"(?<=[。！？!?])\s*", cleaned) if item.strip()]
        if len(sentences) < 6:
            return cleaned

        grouped: list[str] = []
        current: list[str] = []
        for sentence in sentences:
            current.append(sentence)
            if len(current) >= 2:
                grouped.append("".join(current))
                current = []
        if current:
            grouped.append("".join(current))
        return "\n\n".join(grouped)

    def _mock_response(
        self,
        user_input: str,
        planner_output: dict[str, object],
        style_summary: dict[str, str],
    ) -> str:
        has_risk = any(keyword in user_input for keyword in RISK_KEYWORDS)
        persona_name = style_summary["persona_name"]
        opener_map = {
            "温暖倾听者": "你好，我先想认真地告诉你，你现在这么累，并不是因为你不够好，而是你真的已经撑了很久。",
            "理性破局教练": "你好，先把一件事说清楚：你现在遇到的不是“你这个人不行”，而是问题缠在一起之后，让你暂时看不清从哪里下手。",
            "启发故事导师": "你好，读完你的来信，我更想和你一起看见：这件事表面上很乱，里面其实藏着一个可以重新选择的入口。",
        }
        action_line = {
            "概念启发": "这两天先别逼自己一下子想通所有事，只需要把最重的那件事写成两三句，给它一个名字。",
            "结构引导": "也许可以先从一个很小的动作开始：找一个可信任的人开口，把最近最压你的情境写成两三句，再给自己留出一小段不被打断的缓冲时间。",
            "微步实操": "今晚先做一个最小动作：把想说却说不出口的话写进备忘录；明天再把其中一句发给一个值得信任的大人或老师。",
        }

        advice_style = style_summary["advice"]
        intro = opener_map.get(persona_name, opener_map["温暖倾听者"])
        body = (
            "你信里那种又想撑住、又快撑不住的感觉，我能理解。真正需要被看见的，也许不只是那件具体的事，而是你明明还想把生活过好，却一直缺少一个能帮你把问题拆开的支点。"
        )
        reframe = (
            "所以现在更重要的，不是证明自己够不够坚强，而是把问题和你这个人分开看。你在经历困难，这不等于你就是失败的；你需要的是更清楚的边界、更具体的话术，以及一点点重新拿回掌控感的机会。"
        )
        safety = ""
        if has_risk:
            safety = (
                "\n\n另外，我想郑重回应你提到的那些很危险的念头。如果你已经有伤害自己的冲动，请不要一个人扛着，尽快联系你信任的家人、老师、心理老师或当地专业援助。这不是示弱，而是保护自己最勇敢的一步。"
            )

        closing = (
            "\n\n如果你愿意，也可以先从一句最简单的话开始，比如“我最近真的有点扛不住，想找你帮我一起想想办法”。你不用一次说得很完整，被接住这件事，本来就可以从一句话开始。"
            "\n\n愿你先把今天过稳一点点。我会把这份祝福留在这里，也希望你继续给自己一个被照顾、被理解的机会。"
        )

        return "\n\n".join([intro, body, reframe, action_line[advice_style]]) + safety + closing
