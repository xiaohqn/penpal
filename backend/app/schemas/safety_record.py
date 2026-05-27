"""
输入：
- 安全回复保存接口提交的原始来信、风险类型、修正类型、风险原因、原始回复和润色回复。
- 安全回复记录查询接口从数据库 ORM 模型中读取到的字段。
输出：
- 导出安全回复记录保存请求、列表项、列表响应和详情响应的 Pydantic 模型。
作用：
- 这个文件定义安全回复记录相关接口的数据契约，确保前后端在字段结构上保持一致。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SafetyReplyRecordSaveRequest(BaseModel):
    """
    输入：
    - user_input：原始来信，不能为空。
    - risk_labels：模型原始识别出的风险类型列表，至少 1 项。
    - corrected_risk_labels：人工修正后的风险类型列表，至少 1 项。
    - risk_reason：风险原因说明，不能为空。
    - ai_safe_response：模型原始安全回复，不能为空。
    - expert_polished_response：专家润色后的安全回复，不能为空。
    输出：
    - 返回一个经过字段校验与去空白处理的保存请求对象。
    作用：
    - 约束前端提交给安全回复记录保存接口的最小必需信息。
    """

    user_input: str = Field(min_length=1)
    risk_labels: list[str] = Field(min_length=1)
    corrected_risk_labels: list[str] = Field(min_length=1)
    risk_reason: str = Field(min_length=1)
    ai_safe_response: str = Field(min_length=1)
    expert_polished_response: str = Field(min_length=1)

    @field_validator("user_input", "risk_reason", "ai_safe_response", "expert_polished_response")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """去掉关键文本字段首尾空白，并阻止空字符串写入数据库。"""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field cannot be empty")
        return cleaned

    @field_validator("risk_labels", "corrected_risk_labels")
    @classmethod
    def validate_label_list(cls, values: list[str]) -> list[str]:
        """规范风险类型数组，去空白、去空项并保留原始顺序。"""
        cleaned_values: list[str] = []
        for value in values:
            cleaned = value.strip()
            if cleaned and cleaned not in cleaned_values:
                cleaned_values.append(cleaned)
        if not cleaned_values:
            raise ValueError("risk label list cannot be empty")
        return cleaned_values


class SafetyReplyRecordResponse(BaseModel):
    """
    输入：
    - 来自 `SafetyReplyRecord` ORM 模型的一整条安全回复记录。
    输出：
    - 返回前端详情页可直接消费的结构化响应。
    作用：
    - 作为安全回复记录详情和创建成功后的统一响应模型。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    style_name: str
    user_input: str
    risk_labels_json: list[str]
    corrected_risk_labels_json: list[str]
    risk_reason: str
    ai_safe_response: str
    expert_polished_response: str
    created_at: datetime
    updated_at: datetime


class SafetyReplyRecordListItem(BaseModel):
    """
    输入：
    - 安全回复记录列表中的单条 ORM 记录。
    输出：
    - 返回左侧列表表格所需的精简字段。
    作用：
    - 控制列表接口只返回概览信息，避免一次性把详情大字段全部传给前端。
    """

    id: int
    style_name: str
    user_input: str
    created_at: datetime
    updated_at: datetime


class SafetyReplyRecordListResponse(BaseModel):
    """
    输入：
    - 当前页安全回复记录列表、总数和分页参数。
    输出：
    - 返回一个标准分页响应。
    作用：
    - 统一安全回复记录列表接口的响应结构。
    """

    items: list[SafetyReplyRecordListItem]
    total: int
    page: int
    page_size: int
