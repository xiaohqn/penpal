from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import WorkspaceTask
from app.schemas.workspace_task import WorkspaceTaskListResponse, WorkspaceTaskResponse, WorkspaceTaskSaveRequest


class WorkspaceTaskService:
    def list_tasks(
        self,
        db: Session,
        counselor_id: str,
        include_archived: bool = False,
        limit: int = 50,
    ) -> WorkspaceTaskListResponse:
        query = select(WorkspaceTask).where(WorkspaceTask.counselor_id == counselor_id)
        if not include_archived:
            query = query.where(WorkspaceTask.status != "archived")
        tasks = db.scalars(query.order_by(desc(WorkspaceTask.updated_at)).limit(limit)).all()
        return WorkspaceTaskListResponse(
            items=[WorkspaceTaskResponse.model_validate(task) for task in tasks],
            total=len(tasks),
        )

    def get_task(self, db: Session, task_id: int, counselor_id: str) -> WorkspaceTaskResponse | None:
        task = db.get(WorkspaceTask, task_id)
        if task is None or task.counselor_id != counselor_id:
            return None
        return WorkspaceTaskResponse.model_validate(task)

    def latest_in_progress(self, db: Session, counselor_id: str) -> WorkspaceTaskResponse | None:
        task = db.scalar(
            select(WorkspaceTask)
            .where(WorkspaceTask.counselor_id == counselor_id, WorkspaceTask.status.in_(["draft", "in_progress"]))
            .order_by(desc(WorkspaceTask.updated_at))
        )
        return WorkspaceTaskResponse.model_validate(task) if task is not None else None

    def create_task(self, db: Session, counselor_id: str, payload: WorkspaceTaskSaveRequest) -> WorkspaceTaskResponse:
        task = WorkspaceTask(
            counselor_id=counselor_id,
            mode=payload.mode,
            status=payload.status,
            title=payload.title or self._derive_title(payload.summary, payload.state),
            summary=payload.summary,
            state_json=payload.state,
            batch_session_id=payload.batch_session_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return WorkspaceTaskResponse.model_validate(task)

    def update_task(
        self,
        db: Session,
        task_id: int,
        counselor_id: str,
        payload: WorkspaceTaskSaveRequest,
    ) -> WorkspaceTaskResponse | None:
        task = db.get(WorkspaceTask, task_id)
        if task is None or task.counselor_id != counselor_id:
            return None
        task.mode = payload.mode
        task.status = payload.status
        task.title = payload.title or self._derive_title(payload.summary, payload.state)
        task.summary = payload.summary
        task.state_json = payload.state
        task.batch_session_id = payload.batch_session_id
        db.commit()
        db.refresh(task)
        return WorkspaceTaskResponse.model_validate(task)

    def _derive_title(self, summary: str, state: dict) -> str:
        source = summary or str(state.get("userInput") or "")
        compact = " ".join(source.split())
        return compact[:28] or "未命名工单"
