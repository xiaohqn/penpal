from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app.db"
DEFAULT_RAG_SEED_PATH = PROJECT_ROOT.parent / "data" / "seed.json"


class Settings(BaseSettings):
    """
    输入：
    - `.env` 文件、进程环境变量，以及后端运行所需的基础配置项。
    输出：
    - 返回一个集中管理后端配置的 Settings 对象，向外暴露统一的模式判定与路径解析结果。
    作用：
    - 这个类既负责读取原始环境变量，也负责把“planner / generator / safety 实际应该走哪种模式”
      这样的派生逻辑封装成属性，避免业务层到处复制判断条件。
    """

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mindful Copilot API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH}"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    planner_model: str = "gpt-4o-mini"
    generator_model: str = "doubao-1-5-pro-32k-250115"
    planner_mode: Literal["auto", "mock", "api"] = "auto"
    generator_mode: Literal["auto", "mock", "api", "local", "vllm"] = "auto"
    safety_mode: Literal["mock", "api", "local"] = "api"
    compare_model_outputs: bool = False

    gpt_api_key: str | None = None
    gpt_base_url: str = "https://api.chatanywhere.tech/v1"
    doubao_api_key: str | None = None
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    vllm_api_key: str | None = None
    vllm_base_url: str = "http://127.0.0.1:8001/v1"
    vllm_model_name: str = ""

    local_model_path: str | None = None
    local_generator_model_path: str | None = None
    local_device: str = "auto"
    local_dtype: str = "auto"
    local_trust_remote_code: bool = True
    local_generator_max_new_tokens: int = 1024
    local_top_p: float = 0.9

    mock_llm: bool = True
    stream_chunk_size: int = 28
    stream_chunk_delay_ms: int = 15
    rag_seed_path: str = str(DEFAULT_RAG_SEED_PATH)
    rag_seed_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        """
        输入：
        - 原始的 CORS 配置，可能是逗号分隔字符串，也可能已经是列表。
        输出：
        - 返回规范化后的 URL 列表。
        作用：
        - 兼容 `.env` 中常见的字符串写法，同时保证应用层始终拿到统一的数据结构。
        """

        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def effective_planner_mode(self) -> Literal["mock", "api"]:
        """
        输入：
        - `planner_mode`、`mock_llm` 与 `gpt_api_key`。
        输出：
        - 返回 Planner 当前真正采用的模式，只会是 `mock` 或 `api`。
        作用：
        - 把 Planner 的自动模式判定集中起来，供健康检查和业务层统一复用。
        """

        if self.planner_mode != "auto":
            return self.planner_mode
        if self.mock_llm or not self.gpt_api_key:
            return "mock"
        return "api"

    @property
    def effective_generator_mode(self) -> Literal["mock", "api", "local", "vllm"]:
        """
        输入：
        - `generator_mode`、`mock_llm`、vLLM 配置、本地模型路径和 API Key。
        输出：
        - 返回生成主链路真正采用的模式。
        作用：
        - 在 `auto` 下按配置优先级统一决定生成来源，避免前后端、接口层和服务层出现模式理解不一致。
        """

        if self.generator_mode != "auto":
            return self.generator_mode
        if self.mock_llm:
            return "mock"
        if self.vllm_model_name:
            return "vllm"
        if self.local_generator_model_path or self.local_model_path:
            return "local"
        if self.doubao_api_key:
            return "api"
        return "mock"

    @property
    def effective_safety_mode(self) -> Literal["mock", "api", "local"]:
        """
        输入：
        - `safety_mode` 与豆包 API / 本地安全模型相关配置。
        输出：
        - 返回安全检测与安全回复链路真正采用的模式。
        作用：
        - 允许安全链路通过单独的 env 独立于普通草稿生成进行配置，避免再额外引入隐式继承规则。
        """

        return self.safety_mode

    @property
    def use_mock_llm(self) -> bool:
        """
        输入：
        - Planner 与 Generator 的最终模式判定结果。
        输出：
        - 当普通生成主链路整体处于 mock 状态时返回 `True`。
        作用：
        - 给现有主链路逻辑保留一个“整体是否为 mock”快捷判断，不用于安全链路的独立模式决策。
        """

        return self.effective_planner_mode == "mock" and self.effective_generator_mode == "mock"

    def resolve_local_generator_model_path(self) -> Path | None:
        """
        输入：
        - `LOCAL_GENERATOR_MODEL_PATH` 与 `LOCAL_MODEL_PATH`。
        输出：
        - 返回展开后的本地生成模型目录路径；未配置时返回 `None`。
        作用：
        - 统一本地生成模型目录的优先级和路径解析规则，避免调用方自行处理 `~` 和回退关系。
        """

        raw_path = self.local_generator_model_path or self.local_model_path
        if not raw_path:
            return None
        return Path(raw_path).expanduser()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
