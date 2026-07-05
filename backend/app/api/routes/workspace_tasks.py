from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_counselor_id
from app.api.deps import get_db_session, get_workspace_task_service
from app.schemas.workspace_task import WorkspaceTaskListResponse, WorkspaceTaskResponse, WorkspaceTaskSaveRequest
from app.services.workspace_task_service import WorkspaceTaskService

router = APIRouter(prefix="/workspace-tasks", tags=["workspace-tasks"])


@router.get("", response_model=WorkspaceTaskListResponse)
def list_workspace_tasks(
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    service: WorkspaceTaskService = Depends(get_workspace_task_service),
) -> WorkspaceTaskListResponse:
    return service.list_tasks(db=db, counselor_id=counselor_id, include_archived=include_archived, limit=limit)


@router.get("/latest", response_model=WorkspaceTaskResponse | None)
def latest_workspace_task(
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    service: WorkspaceTaskService = Depends(get_workspace_task_service),
) -> WorkspaceTaskResponse | None:
    return service.latest_in_progress(db=db, counselor_id=counselor_id)


@router.get("/{task_id}", response_model=WorkspaceTaskResponse)
def get_workspace_task(
    task_id: int,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    service: WorkspaceTaskService = Depends(get_workspace_task_service),
) -> WorkspaceTaskResponse:
    task = service.get_task(db=db, task_id=task_id, counselor_id=counselor_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace task not found")
    return task


@router.post("", response_model=WorkspaceTaskResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_task(
    payload: WorkspaceTaskSaveRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    service: WorkspaceTaskService = Depends(get_workspace_task_service),
) -> WorkspaceTaskResponse:
    return service.create_task(db=db, counselor_id=counselor_id, payload=payload)


@router.put("/{task_id}", response_model=WorkspaceTaskResponse)
def update_workspace_task(
    task_id: int,
    payload: WorkspaceTaskSaveRequest,
    counselor_id: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    service: WorkspaceTaskService = Depends(get_workspace_task_service),
) -> WorkspaceTaskResponse:
    task = service.update_task(db=db, task_id=task_id, counselor_id=counselor_id, payload=payload)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace task not found")
    return task
