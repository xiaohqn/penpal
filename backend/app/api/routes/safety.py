"""
输入：
- 前端提交的安全检测请求体，或针对当前安全回复的批注重生成请求体。
- 依赖注入提供的 `SafetyService`。
输出：
- 返回当前来信的安全检测结果，或基于专家批注重生成后的安全回复候选。
作用：
- 对外暴露 `penpal` 的安全检测、安全回复与安全回复重生成接口。
"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_safety_service
from app.schemas.safety import (
    SafetyCheckRequest,
    SafetyCheckResponse,
    SafetyRegenerateRequest,
    SafetyResponseCandidate,
)
from app.services.safety_service import SafetyModeUnavailableError, SafetyService

router = APIRouter(prefix="/safety", tags=["safety"])


@router.post("/check", response_model=SafetyCheckResponse)
async def check_safety(
    payload: SafetyCheckRequest,
    safety_service: SafetyService = Depends(get_safety_service),
) -> SafetyCheckResponse:
    """
    输入：
    - payload：前端提交的来信正文。
    - safety_service：安全检测与安全回复业务服务。
    输出：
    - 返回结构化安全检测结果。
    作用：
    - 让工作台可以在进入普通人格生成前，先判断是否需要切到安全回复流程。
    """

    try:
        return await safety_service.check_user_input(
            payload.user_input,
            source_mode=payload.source_mode,
        )
    except SafetyModeUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/regenerate", response_model=SafetyResponseCandidate)
async def regenerate_safety_reply(
    payload: SafetyRegenerateRequest,
    safety_service: SafetyService = Depends(get_safety_service),
) -> SafetyResponseCandidate:
    """
    输入：
    - payload：前端提交的原始来信、当前安全回复、划词批注和专家总体说明。
    - safety_service：安全检测与安全回复业务服务。
    输出：
    - 返回一条基于专家批注重新生成后的安全回复候选。
    作用：
    - 让安全回复页也能像普通对话一样，根据专家对当前回复的批注快速生成更贴近人工意图的新版本。
    """

    try:
        return await safety_service.regenerate_safe_response_from_annotations(
            user_input=payload.user_input,
            risk_codes=payload.risk_codes,
            corrected_risk_labels=payload.corrected_risk_labels,
            risk_reason=payload.risk_reason,
            current_response=payload.current_response,
            source_annotations=[annotation.model_dump() for annotation in payload.source_annotations],
            expert_annotation=payload.expert_annotation,
            source=payload.source,
        )
    except (SafetyModeUnavailableError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
