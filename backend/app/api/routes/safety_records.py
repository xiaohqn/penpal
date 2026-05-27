"""
输入：
- 前端对安全回复记录的创建、列表、详情、删除和导出请求。
- 依赖注入提供的数据库会话、`SafetyRecordService` 与 `ExcelService`。
输出：
- 返回安全回复记录的创建结果、分页列表、详情响应、删除结果或导出文件。
作用：
- 这个路由文件对外暴露安全回复记录 API，使前端能够独立保存、查看和导出安全回复样本库。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_excel_service, get_safety_record_service
from app.schemas.safety_record import (
    SafetyReplyRecordListResponse,
    SafetyReplyRecordResponse,
    SafetyReplyRecordSaveRequest,
)
from app.services.excel_service import ExcelService
from app.services.safety_record_service import SafetyRecordService

router = APIRouter(prefix="/safety-records", tags=["safety-records"])


@router.post(
    "",
    response_model=SafetyReplyRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_safety_record(
    payload: SafetyReplyRecordSaveRequest,
    db: Session = Depends(get_db_session),
    safety_record_service: SafetyRecordService = Depends(get_safety_record_service),
) -> SafetyReplyRecordResponse:
    """
    输入：
    - payload：前端提交的安全回复保存数据。
    - db：数据库会话。
    - safety_record_service：安全回复记录业务服务。
    输出：
    - 返回新建完成后的安全回复记录详情。
    作用：
    - 提供安全回复记录的创建接口。
    """

    return safety_record_service.create_record(db=db, payload=payload)


@router.get("", response_model=SafetyReplyRecordListResponse)
def list_safety_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db_session),
    safety_record_service: SafetyRecordService = Depends(get_safety_record_service),
) -> SafetyReplyRecordListResponse:
    """
    输入：
    - page / page_size：分页参数。
    - db：数据库会话。
    - safety_record_service：安全回复记录业务服务。
    输出：
    - 返回当前页安全回复记录列表。
    作用：
    - 提供安全回复记录历史页左侧表格的数据源。
    """

    return safety_record_service.list_records(db=db, page=page, page_size=page_size)


@router.get("/export")
def export_safety_records_excel(
    db: Session = Depends(get_db_session),
    safety_record_service: SafetyRecordService = Depends(get_safety_record_service),
    excel_service: ExcelService = Depends(get_excel_service),
) -> Response:
    """
    输入：
    - db：数据库会话。
    - safety_record_service：安全回复记录业务服务。
    - excel_service：Excel 导出服务。
    输出：
    - 返回一个包含全部安全回复记录的 Excel 文件响应。
    作用：
    - 为历史页里的“安全回复记录导出”按钮提供后端数据源和文件生成能力。
    """

    records = safety_record_service.get_all_records_for_export(db=db)
    content = excel_service.export_safety_records_excel(records)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="safety_reply_records.xlsx"'},
    )


@router.get("/{record_id}", response_model=SafetyReplyRecordResponse)
def get_safety_record(
    record_id: int,
    db: Session = Depends(get_db_session),
    safety_record_service: SafetyRecordService = Depends(get_safety_record_service),
) -> SafetyReplyRecordResponse:
    """
    输入：
    - record_id：要读取的安全回复记录 ID。
    - db：数据库会话。
    - safety_record_service：安全回复记录业务服务。
    输出：
    - 返回对应的安全回复记录详情；不存在时返回 404。
    作用：
    - 提供安全回复记录详情接口。
    """

    record = safety_record_service.get_record(db=db, record_id=record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety record not found")
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_safety_record(
    record_id: int,
    db: Session = Depends(get_db_session),
    safety_record_service: SafetyRecordService = Depends(get_safety_record_service),
) -> Response:
    """
    输入：
    - record_id：要删除的安全回复记录 ID。
    - db：数据库会话。
    - safety_record_service：安全回复记录业务服务。
    输出：
    - 删除成功时返回空响应；记录不存在时返回 404。
    作用：
    - 提供安全回复记录删除接口，支持前端在历史样本库中移除不需要的安全数据。
    """

    deleted = safety_record_service.delete_record(db=db, record_id=record_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety record not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
