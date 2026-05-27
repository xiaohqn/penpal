"""
输入：
- `/safety/check` 接口接收的来信文本。
- 安全检测链路生成的风险标签、风险原因、安全回复，以及从安全回复中二次提取出的高亮片段。
输出：
- 导出安全检测接口的请求与响应数据模型。
作用：
- 统一约束安全检测接口的数据格式，让前端既能读取完整安全回复，也能读取需要重点高亮的安全部分及其来源。
"""

from pydantic import BaseModel, Field, field_validator


class SafetyCheckRequest(BaseModel):
    """
    输入：
    - user_input：前端提交的来信正文，要求是非空字符串。
    输出：
    - 返回通过校验和清洗后的请求模型。
    作用：
    - 防止空白来信进入安全检测和安全回复生成流程。
    """

    user_input: str = Field(min_length=1, max_length=5000)
    source_mode: str = "auto"

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("user_input cannot be empty")
        return cleaned

    @field_validator("source_mode")
    @classmethod
    def validate_source_mode(cls, value: str) -> str:
        """
        输入：
        - 前端当前选中的生成来源模式字符串。
        输出：
        - 返回标准化后的模式值，只允许 `auto`、`api`、`vllm` 或 `compare`。
        作用：
        - 让安全检测接口也能感知工作台当前的来源选择，从而避免用户明明点了 `vLLM`，
          安全链路却无提示地继续回退到 API。
        """

        normalized = value.strip().lower()
        if normalized not in {"auto", "api", "vllm", "compare"}:
            raise ValueError("source_mode must be one of: auto, api, vllm, compare")
        return normalized


class SafetyResponseCandidate(BaseModel):
    """
    输入：
    - source：当前安全回复候选来自哪条生成链路，便于前端在对比模式下区分 `api` 和 `local`。
    - source_label：面向前端展示的来源名称，例如“API 安全回复”或“本地安全模型安全回复”。
    - intent：该候选安全回复对应的风险承接意图总结。
    - safe_response：该候选的完整安全回复正文。
    - safe_highlight_segments：该候选安全回复中需要重点高亮的安全片段。
    - safe_highlight_source：高亮片段是通过大模型提取还是兜底规则提取得到的来源标记。
    输出：
    - 返回单个安全回复候选的结构化数据。
    作用：
    - 让安全链路在对比模式下可以同时返回多份候选回复，同时仍然保持每份候选都带有自己独立的高亮结果。
    """

    source: str
    source_label: str
    intent: str | None = None
    safe_response: str
    safe_highlight_segments: list[str] = Field(default_factory=list)
    safe_highlight_source: str | None = None


class SafetySourceAnnotationNote(BaseModel):
    """
    输入：
    - id：前端为单条安全回复高亮批注生成的唯一标识。
    - start / end：批注对应文本在当前安全回复里的起止字符位置，必须是非负整数。
    - quote：被专家高亮选中的原始回复片段。
    - note：专家对该片段的修改意见、风险提醒或补充说明。
    - color：前端展示该批注时使用的颜色标记，默认沿用 `amber`。
    输出：
    - 返回通过基础校验后的安全回复高亮批注对象。
    作用：
    - 让安全回复重生成接口可以像普通对话一样，稳定接收“划词 + 批注说明”的结构化数据。
    """

    id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str = ""
    note: str = ""
    color: str = "amber"


class SafetyRegenerateRequest(BaseModel):
    """
    输入：
    - user_input：原始高风险来信正文，重生成时仍以它作为主要上下文。
    - risk_codes：当前风险链路保留的原始风险编号，供后端在人工标签无法完全映射时兜底。
    - corrected_risk_labels：人工修正后的风险标签，用于 few-shot 检索和更贴近人工判断的生成控制。
    - risk_reason：本轮风险识别或人工修正后保留的风险原因说明。
    - source：当前要重生成的安全回复来源，例如 `api`、`local` 或 `mock`。
    - current_response：当前正在被专家批注的安全回复正文。
    - source_annotations：专家在当前安全回复上留下的高亮批注列表。
    - expert_annotation：专家对整条安全回复的总体说明或额外要求。
    输出：
    - 返回一份通过校验和清洗后的安全回复批注重生成请求。
    作用：
    - 为 `/safety/regenerate` 提供独立的数据契约，避免把“当前回复 + 批注说明”误当成新的安全检测请求。
    """

    user_input: str = Field(min_length=1, max_length=5000)
    risk_codes: list[int] = Field(min_length=1)
    corrected_risk_labels: list[str] = Field(default_factory=list)
    risk_reason: str = ""
    source: str = "api"
    current_response: str = ""
    source_annotations: list[SafetySourceAnnotationNote] = Field(default_factory=list)
    expert_annotation: str = ""

    @field_validator("user_input", "risk_reason", "current_response", "expert_annotation")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        """
        输入：
        - 文本型请求字段原始值。
        输出：
        - 返回去掉首尾空白后的文本；对必填字段会在最小长度约束之外进一步保证内容干净。
        作用：
        - 防止批注重生成链路把无意义的空白文本拼进提示词里，影响模型对专家意图的理解。
        """

        return value.strip()

    @field_validator("corrected_risk_labels")
    @classmethod
    def strip_corrected_risk_labels(cls, value: list[str]) -> list[str]:
        """
        输入：
        - 前端提交的人工修正风险标签列表。
        输出：
        - 返回去重前的清洗结果，移除空白标签项。
        作用：
        - 让 few-shot 检索和风险编号映射只处理真正有效的人工标签，避免空字符串污染后续逻辑。
        """

        return [label.strip() for label in value if label.strip()]

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        """
        输入：
        - 当前安全回复候选的来源标记。
        输出：
        - 返回标准化后的来源值，只允许 `api`、`local` 或 `mock`。
        作用：
        - 让安全回复重生成始终针对用户眼前正在查看的那条候选回复，而不是隐式切到别的链路。
        """

        normalized = value.strip().lower()
        if normalized not in {"api", "local", "mock"}:
            raise ValueError("source must be one of: api, local, mock")
        return normalized


class SafetyCheckResponse(BaseModel):
    """
    输入：
    - 风险检测阶段识别出的风险代码、风险标签、风险原因和是否安全结果。
    - 不安全场景下生成的安全回复，以及从该回复中抽取出来的高亮片段和提取来源。
    - 对比模式下返回的多份安全回复候选，每份候选都有各自独立的来源和高亮信息。
    输出：
    - 返回统一的安全检测接口响应模型。
    作用：
    - 为前端提供完整的安全回复展示数据，并额外附带可直接高亮的安全片段、调试来源标记，
      以及安全对比模式需要的候选列表。
    """

    risk_codes: list[int]
    risk_labels: list[str]
    reason: str
    is_safe: bool
    intent: str | None = None
    safe_response: str | None = None
    safe_highlight_segments: list[str] = Field(default_factory=list)
    safe_highlight_source: str | None = None
    safe_response_candidates: list[SafetyResponseCandidate] = Field(default_factory=list)
