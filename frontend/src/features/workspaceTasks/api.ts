import { request } from "../../lib/request";
import type { WorkspaceTask, WorkspaceTaskListResponse, WorkspaceTaskSavePayload } from "./types";

export function fetchWorkspaceTasks() {
  return request<WorkspaceTaskListResponse>("/workspace-tasks");
}

export function fetchLatestWorkspaceTask() {
  return request<WorkspaceTask | null>("/workspace-tasks/latest");
}

export function fetchWorkspaceTask(taskId: number) {
  return request<WorkspaceTask>(`/workspace-tasks/${taskId}`);
}

export function createWorkspaceTask(payload: WorkspaceTaskSavePayload) {
  return request<WorkspaceTask>("/workspace-tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateWorkspaceTask(taskId: number, payload: WorkspaceTaskSavePayload) {
  return request<WorkspaceTask>(`/workspace-tasks/${taskId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
