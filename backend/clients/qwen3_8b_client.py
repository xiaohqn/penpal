"""
输入：
- 调用方传入的对话消息列表、可选 LoRA 路径，以及运行环境中的本地模型路径配置。
- 优先读取 `backend/.env` 对应的本地模型路径配置；如果没有，再回退到环境变量
  `QWEN3_8B_MODEL_PATH`、`LOCAL_GENERATOR_MODEL_PATH` 或 `LOCAL_MODEL_PATH`。
输出：
- 返回本地 Qwen3-8B 模型的批量生成结果；当前 `close()` 无额外副作用，仅保留统一接口。
作用：
- 这个文件为安全检测、安全回复和高亮提取提供本地模型分支。
  当主链路切到 `vllm` 并要求安全链路走 `if_local=True` 时，这里负责解析本地模型路径并执行生成。
"""
import os

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest


def _load_backend_settings():
    """
    输入：
    - 无显式参数；内部尝试导入后端的 `get_settings()`。
    输出：
    - 成功时返回 Settings 实例；失败时返回 `None`。
    作用：
    - 让本地安全模型分支优先复用 `backend/.env` 中已经配置好的模型目录，减少额外环境变量依赖。
    """

    try:
        from app.core.config import get_settings
    except Exception:
        return None

    try:
        return get_settings()
    except Exception:
        return None

def create_qwen3_8b_client(model_path: str | None = None):
    """
    输入：
    - model_path：显式指定的本地模型路径；未传时依次从环境变量或默认路径推断。
    输出：
    - 返回已加载配置的 `Qwen38BClient` 实例。
    作用：
    - 把本地安全模型的路径解析集中在一个工厂函数里，避免不同调用点各自硬编码路径，
      也方便项目迁移到其他机器时只通过环境变量切换模型目录。
    """

    settings = _load_backend_settings()
    resolved_settings_path = settings.resolve_local_generator_model_path() if settings else None
    resolved_model_path = (
        model_path
        or (str(resolved_settings_path) if resolved_settings_path is not None else None)
        or os.getenv("QWEN3_8B_MODEL_PATH")
        or os.getenv("LOCAL_GENERATOR_MODEL_PATH")
        or os.getenv("LOCAL_MODEL_PATH")
        or "/home/share/models/Qwen3-8B"
    )
    return Qwen38BClient(resolved_model_path)

class Qwen38BClient:
    """
    输入：
    - model_path：vLLM 需要加载的本地模型目录。
    输出：
    - 构造一个具备 `batch_generate` / `close` 接口的本地模型客户端实例。
    作用：
    - 统一封装 vLLM 的本地聊天调用，让安全链路在 `if_local=True` 时可以复用与远端客户端相似的接口。
    """

    def __init__(self, model_path: str ):
        self.llm = LLM(model=model_path, enable_lora=True)

    def batch_generate(self, prompts: list[dict], **kwargs):
        """
        输入：
        - prompts：批量聊天消息列表。
        - kwargs：可选的 `lora_path` 等额外推理参数。
        输出：
        - 返回与输入顺序一致的生成文本列表。
        作用：
        - 用统一的采样参数执行本地批量生成，并在传入 LoRA 路径时启用对应增量权重。
        """

        # 这里保持与原始脚本接近的采样策略，避免迁移后安全链路的文本风格大幅变化。
        sampling_params = SamplingParams(temperature=0.6, top_p=0.95, top_k=20, max_tokens=32768)
        if "lora_path" in kwargs:
            lora_path = kwargs["lora_path"]
            print(f"use lora: {lora_path}")
            outputs = self.llm.chat(prompts, 
                                    sampling_params,
                                    lora_request=LoRARequest("v1_2_lora", 1, lora_path),
                                    chat_template_kwargs={"enable_thinking": False},  # Set to False to strictly disable thinking
                            )
        else:
            outputs = self.llm.chat(prompts, 
                                    sampling_params,
                                    chat_template_kwargs={"enable_thinking": False},  # Set to False to strictly disable thinking
                            )
        results = []
        for output in outputs:
            result = output.outputs[0].text
            results.append(result)
        return results

    def close(self):
        """
        输入：
        - 无显式参数。
        输出：
        - 无返回值，也不做额外资源释放。
        作用：
        - 保持与远端客户端一致的接口形状，方便上层安全链路统一调用 `close()`。
        """

        pass

def main():
    # Create an LLM.
    client = create_qwen3_8b_client()
    # Sample prompts.
    conversation = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hello! How can I assist you today?"},
        {
            "role": "user",
            "content": "Write an essay about the importance of higher education.",
        },
    ]
    outputs = client.batch_generate(conversation, max_workers=4)
    
    # Print the outputs.
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
