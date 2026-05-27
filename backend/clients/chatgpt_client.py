#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入：
- 调用方传入的消息列表、模型名、采样参数，以及运行环境中的 OpenAI/GPT API 配置。
- 优先读取 `backend/.env` 对应的 Settings 中的 Planner 配置；如果没有，再回退到环境变量
  `GPT_API_KEY` / `OPENAI_API_KEY` / `CHATGPT_API_KEY`，以及可选的
  `GPT_BASE_URL` / `OPENAI_BASE_URL` / `CHATGPT_BASE_URL`。
输出：
- 返回模型生成的文本结果、流式片段或批量生成结果；失败时抛出带上下文的异常。
作用：
- 这个文件封装独立脚本兼容用的 OpenAI 风格客户端，并把密钥与网关地址改成从环境读取，
  避免把特定账号配置写死在仓库中，方便项目迁移到其他环境时直接复用。
"""

import os
import threading
import queue
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
try:
    from tqdm import tqdm
except Exception:
    tqdm = None

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("请先安装openai库: pip install openai", file=sys.stderr)
    raise

from clients.base_client import ModelConfig
from clients.base_client import BaseClient


def _load_backend_settings():
    """
    输入：
    - 无显式参数；内部尝试导入后端的 `get_settings()`。
    输出：
    - 成功时返回 Settings 实例；拿不到后端配置模块时返回 `None`。
    作用：
    - 让旧兼容脚本也能和 FastAPI 服务共用 `backend/.env` 中的 Planner 配置来源，
      避免同一个项目里同时维护两套 GPT key 配置。
    """

    try:
        from app.core.config import get_settings
    except Exception:
        return None

    try:
        return get_settings()
    except Exception:
        return None

@dataclass
class ChatGPTConfig(ModelConfig):
    api_key: str
    model: str
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30
    base_url: str = "https://api.openai.com/v1"

class ChatGPTClient(BaseClient):
    def __init__(self, config: ChatGPTConfig, threads=10):
        self.config = config
        self.threads = threads
        self._lock = threading.Lock()
        self._thread_pool = None
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )

    def _get_thread_pool(self):
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.threads)
        return self._thread_pool

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        try:
            request_params = {
                "model": model or self.config.model,
                "messages": messages,
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
            }
            request_params.update(kwargs)
            response = self.client.chat.completions.create(**request_params)
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            else:
                raise Exception("响应格式错误: 无法提取回复内容")
        except openai.OpenAIError as e:
            raise Exception(f"OpenAI错误: {str(e)}")
        except Exception as e:
            raise Exception(f"ChatGPT请求出错: {str(e)}")

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        try:
            request_params = {
                "model": model or self.config.model,
                "messages": messages,
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
                "stream": True,
            }
            request_params.update(kwargs)
            stream = self.client.chat.completions.create(**request_params)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except openai.OpenAIError as e:
            raise Exception(f"OpenAI错误: {str(e)}")
        except Exception as e:
            raise Exception(f"ChatGPT流式请求出错: {str(e)}")

    def get_available_models(self) -> List[str]:
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            print(f"获取OpenAI模型列表失败: {e}")
            return []

    def batch_generate(
        self,
        messages_list: List[List[Dict[str, str]]],
        models: Optional[List[str]] = None,
        max_workers: Optional[int] = None,
        **kwargs
    ) -> List[str]:
        if max_workers is None:
            max_workers = self.threads
        results: List[Optional[str]] = [None] * len(messages_list)
        total = len(messages_list)
        pb = tqdm(total=total, desc="批量生成", unit="req") if tqdm else None
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {}
            for i, messages in enumerate(messages_list):
                model = models[i] if models and i < len(models) else None
                future = executor.submit(self._generate_single, messages, model, **kwargs)
                future_to_index[future] = i
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = f"错误: {str(e)}"
                results[idx] = result
                if pb:
                    pb.update(1)
        if pb:
            pb.close()
        return results

    def _generate_single(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        try:
            model_to_use = model or self.config.model
            request_params = {
                "model": model_to_use,
                "messages": messages,
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                "temperature": kwargs.get('temperature', self.config.temperature),
            }
            request_params.update(kwargs)
            response = self.client.chat.completions.create(**request_params)
            result = response.choices[0].message.content
            return result
        except Exception as e:
            raise Exception(f"OpenAI调用失败: {str(e)}")

    def batch_stream_generate(
        self,
        messages_list: List[List[Dict[str, str]]],
        models: Optional[List[str]] = None,
        max_workers: Optional[int] = None,
        **kwargs
    ):
        if max_workers is None:
            max_workers = self.threads
        result_queue = queue.Queue()

        def _stream_worker(index, messages, model):
            try:
                model_to_use = model or self.config.model
                request_params = {
                    "model": model_to_use,
                    "messages": messages,
                    "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                    "temperature": kwargs.get('temperature', self.config.temperature),
                    "stream": True,
                }
                request_params.update(kwargs)
                stream = self.client.chat.completions.create(**request_params)
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        result_queue.put((index, chunk.choices[0].delta.content))
            except Exception as e:
                result_queue.put((index, f"错误: {str(e)}"))
            finally:
                result_queue.put((index, None))

        threads = []
        for i, messages in enumerate(messages_list):
            model = models[i] if models and i < len(models) else None
            thread = threading.Thread(target=_stream_worker, args=(i, messages, model))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        total = len(messages_list)
        pb = tqdm(total=total, desc="并行流式", unit="req") if tqdm else None
        completed = set()
        while len(completed) < len(messages_list):
            try:
                index, content = result_queue.get(timeout=1.0)
                if content is None:
                    completed.add(index)
                    if pb:
                        pb.update(1)
                else:
                    yield (index, content)
            except queue.Empty:
                continue

        for thread in threads:
            thread.join()
        if pb:
            pb.close()

    def close(self):
        if self._thread_pool is not None:
            with self._lock:
                if self._thread_pool is not None:
                    self._thread_pool.shutdown(wait=True)
                    self._thread_pool = None

    def __del__(self):
        self.close()

def create_chatgpt_client(model: str = None, **kwargs) -> ChatGPTClient:
    """
    输入：
    - model：调用时使用的模型名称；如果不传，则回退到环境变量或默认值。
    - kwargs：其他客户端配置项；显式传入 `api_key` 或 `base_url` 时优先级最高。
    输出：
    - 返回配置完成的 `ChatGPTClient` 实例。
    作用：
    - 为保留下来的兼容脚本提供统一的 OpenAI 风格客户端工厂，并优先从 `backend/.env`
      读取 Planner 配置；这样独立脚本和 Web 服务会共用同一套 key 与 base URL。
    """

    settings = _load_backend_settings()
    api_key = (
        kwargs.pop("api_key", None)
        or getattr(settings, "gpt_api_key", None)
        or os.getenv("GPT_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("CHATGPT_API_KEY")
    )
    if not api_key:
        raise ValueError("未找到 OpenAI API Key，请在 backend/.env 中设置 GPT_API_KEY，或提供 OPENAI_API_KEY")
    base_url = (
        kwargs.pop("base_url", None)
        or getattr(settings, "gpt_base_url", None)
        or os.getenv("GPT_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("CHATGPT_BASE_URL")
        or "https://api.chatanywhere.tech/v1"
    )
    model = (
        model
        or getattr(settings, "planner_model", None)
        or os.getenv("GPT_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o"
    )
    config = ChatGPTConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        **kwargs
    )
    return ChatGPTClient(config)

if __name__ == "__main__":
    print("ChatGPT API客户端示例 - 多线程版本")
    print("=" * 60)
    try:
        client = create_chatgpt_client()
        messages = [{"role": "user", "content": "用50字介绍Python的特点"}]
        print("ChatGPT: ", end="", flush=True)
        for chunk in client.stream_generate(messages):
            print(chunk, end="", flush=True)
        print()
    except Exception as e:
        print(f"错误: {e}")
