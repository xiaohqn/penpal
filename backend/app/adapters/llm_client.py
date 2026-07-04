import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings


class LLMClientError(RuntimeError):
    pass


@dataclass
class LocalModelBundle:
    tokenizer: Any
    model: Any
    device: str


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._planner_client = (
            AsyncOpenAI(api_key=settings.gpt_api_key, base_url=settings.gpt_base_url)
            if settings.gpt_api_key
            else None
        )
        self._generator_client = (
            AsyncOpenAI(api_key=settings.doubao_api_key, base_url=settings.doubao_base_url)
            if settings.doubao_api_key
            else None
        )
        self._vllm_client = (
            AsyncOpenAI(
                api_key=settings.vllm_api_key or "EMPTY",
                base_url=settings.vllm_base_url,
            )
            if settings.vllm_base_url
            else None
        )
        self._local_models: dict[str, LocalModelBundle] = {}
        self._local_model_lock = Lock()
        self._local_generation_lock = Lock()

    async def complete_api(
        self,
        provider: str,
        model: str,
        messages: Sequence[dict[str, str]],
        temperature: float,
        timeout: int = 60,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        if provider == "gpt":
            client = self._planner_client
        elif provider == "vllm":
            client = self._vllm_client
        else:
            client = self._generator_client
        if client is None:
            raise LLMClientError(f"Provider {provider} is not configured")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=list(messages),
                temperature=temperature,
                timeout=timeout,
                extra_body=extra_body or None,
            )
        except Exception as exc:  # pragma: no cover - depends on network/provider
            raise LLMClientError(f"{provider} completion failed: {exc}") from exc

        return response.choices[0].message.content or ""

    async def stream_api(
        self,
        provider: str,
        model: str,
        messages: Sequence[dict[str, str]],
        temperature: float,
        timeout: int = 60,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        if provider == "gpt":
            client = self._planner_client
        elif provider == "vllm":
            client = self._vllm_client
        else:
            client = self._generator_client
        if client is None:
            raise LLMClientError(f"Provider {provider} is not configured")

        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=list(messages),
                temperature=temperature,
                timeout=timeout,
                stream=True,
                extra_body=extra_body or None,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as exc:  # pragma: no cover - depends on network/provider
            raise LLMClientError(f"{provider} stream failed: {exc}") from exc

    async def complete_local(
        self,
        model_path: str | Path,
        messages: Sequence[dict[str, str]],
        temperature: float,
        max_new_tokens: int,
    ) -> str:
        model_path = str(Path(model_path).expanduser())
        return await asyncio.to_thread(
            self._complete_local_sync,
            model_path,
            list(messages),
            temperature,
            max_new_tokens,
        )

    def _complete_local_sync(
        self,
        model_path: str,
        messages: Sequence[dict[str, str]],
        temperature: float,
        max_new_tokens: int,
    ) -> str:
        bundle = self._get_or_load_local_model(model_path)
        with self._local_generation_lock:
            return self._generate_local_text(
                bundle=bundle,
                messages=messages,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )

    def _get_or_load_local_model(self, model_path: str) -> LocalModelBundle:
        with self._local_model_lock:
            existing = self._local_models.get(model_path)
            if existing is not None:
                return existing

            bundle = self._load_local_model(model_path)
            self._local_models[model_path] = bundle
            return bundle

    def _load_local_model(self, model_path: str) -> LocalModelBundle:
        model_dir = Path(model_path)
        if not model_dir.exists():
            raise LLMClientError(f"Local model path does not exist: {model_dir}")

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise LLMClientError(
                "Local model mode requires torch and transformers. "
                "Please install them first, for example: pip install torch transformers sentencepiece"
            ) from exc

        device = self._resolve_local_device(torch)
        torch_dtype = self._resolve_torch_dtype(torch, device)

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_dir,
                trust_remote_code=self.settings.local_trust_remote_code,
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                trust_remote_code=self.settings.local_trust_remote_code,
                torch_dtype=torch_dtype,
            )
        except Exception as exc:  # pragma: no cover - depends on local model files
            raise LLMClientError(f"Failed to load local model from {model_dir}: {exc}") from exc

        if tokenizer.pad_token is None and tokenizer.eos_token is not None:
            tokenizer.pad_token = tokenizer.eos_token
        if getattr(model.generation_config, "pad_token_id", None) is None and tokenizer.pad_token_id is not None:
            model.generation_config.pad_token_id = tokenizer.pad_token_id

        try:
            model.to(device)
            model.eval()
        except Exception as exc:  # pragma: no cover - depends on device/model compatibility
            raise LLMClientError(f"Failed to move local model to device {device}: {exc}") from exc

        return LocalModelBundle(tokenizer=tokenizer, model=model, device=device)

    def _generate_local_text(
        self,
        bundle: LocalModelBundle,
        messages: Sequence[dict[str, str]],
        temperature: float,
        max_new_tokens: int,
    ) -> str:
        try:
            import torch
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise LLMClientError("Local model mode requires torch to run generation") from exc

        prompt = self._render_local_prompt(bundle.tokenizer, messages)
        inputs = bundle.tokenizer(prompt, return_tensors="pt")
        inputs = {key: value.to(bundle.device) for key, value in inputs.items()}
        prompt_length = inputs["input_ids"].shape[-1]

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0,
            "pad_token_id": bundle.tokenizer.pad_token_id or bundle.tokenizer.eos_token_id,
        }
        if temperature > 0:
            generation_kwargs["temperature"] = temperature
            generation_kwargs["top_p"] = self.settings.local_top_p

        try:
            with torch.no_grad():
                output_ids = bundle.model.generate(**inputs, **generation_kwargs)
        except Exception as exc:  # pragma: no cover - depends on local model/device
            raise LLMClientError(f"Local generation failed: {exc}") from exc

        generated_ids = output_ids[0][prompt_length:]
        return bundle.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    def _render_local_prompt(
        self,
        tokenizer: Any,
        messages: Sequence[dict[str, str]],
    ) -> str:
        if hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", None):
            return tokenizer.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )

        prompt_parts = []
        for message in messages:
            role = message.get("role", "user").upper()
            content = message.get("content", "")
            prompt_parts.append(f"{role}:\n{content}")
        prompt_parts.append("ASSISTANT:\n")
        return "\n\n".join(prompt_parts)

    def _resolve_local_device(self, torch: Any) -> str:
        configured = self.settings.local_device.lower()
        if configured != "auto":
            return configured
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _resolve_torch_dtype(self, torch: Any, device: str) -> Any | None:
        configured = self.settings.local_dtype.lower()
        if configured == "float16":
            return torch.float16
        if configured == "bfloat16":
            return torch.bfloat16
        if configured == "float32":
            return torch.float32
        if device in {"cuda", "mps"}:
            return torch.float16
        return torch.float32
