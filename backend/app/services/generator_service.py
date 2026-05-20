import asyncio

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
            return {"raw": "", "response": response}

        if mode == "local":
            local_model_path = self.settings.resolve_local_generator_model_path()
            if local_model_path is None:
                raise ValueError("LOCAL_MODEL_PATH or LOCAL_GENERATOR_MODEL_PATH is not configured")

            raw = await self.llm_client.complete_local(
                model_path=local_model_path,
                messages=generator_messages,
                temperature=0.7,
                max_new_tokens=self.settings.local_generator_max_new_tokens,
            )
        elif mode == "vllm":
            if not self.settings.vllm_model_name:
                raise ValueError("VLLM_MODEL_NAME is not configured")
            raw = await self.llm_client.complete_api(
                provider="vllm",
                model=self.settings.vllm_model_name,
                messages=generator_messages,
                temperature=0.7,
            )
        else:
            raw = await self.llm_client.complete_api(
                provider="doubao",
                model=self.settings.generator_model,
                messages=generator_messages,
                temperature=0.7,
            )
        response, _ = parse_response_only(raw)
        return {"raw": raw, "response": response}

    def split_text(self, text: str) -> list[str]:
        chunk_size = max(1, self.settings.stream_chunk_size)
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)] or [""]

    async def emit_chunks(self, text: str):
        for chunk in self.split_text(text):
            yield chunk
            if self.settings.stream_chunk_delay_ms > 0:
                await asyncio.sleep(self.settings.stream_chunk_delay_ms / 1000)

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
            "理性教练": "你好，你现在的混乱感并不等于你没有能力，更像是压力已经超出了你一个人硬扛的范围。",
            "故事导师": "你好，读完你的来信，我想到很多人在成长里都会遇到某个突然失重的阶段，你现在就在这样的阶段里。",
            "犀利破局者": "你好，先把一件事说清楚：眼前的困局很重，但它不是对你价值的宣判。",
            "哲理长者": "你好，人被难处压住的时候，最容易把一时的阴影误当成整片天空，而你现在最需要的，是有人陪你把天色重新看清。",
        }
        action_line = {
            "概念启发": "这两天先别逼自己一下子想通所有事，只需要把最重的那件事写成两三句，给它一个名字。",
            "框架策略": "你可以先做三件小事：找一个可信任的人开口；把最近最压你的情境写下来；给自己留出一个不被打断的短时间缓冲。",
            "微步实操": "今晚先做一个最小动作：把想说却说不出口的话写进备忘录；明天再把其中一句发给一个值得信任的大人或老师。",
        }

        advice_style = style_summary["advice"]
        intro = opener_map.get(persona_name, opener_map["温暖倾听者"])
        body = (
            "你信里那种又想撑住、又快撑不住的感觉，我能理解。很多时候，真正把人压垮的，不只是事情本身，而是长期没有被看见、没有地方安放的紧绷。"
        )
        reframe = (
            "所以现在更重要的，不是证明自己够不够坚强，而是把问题和你这个人分开看。你在经历困难，这不等于你就是失败的。"
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
