import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createWorkspaceTask,
  fetchLatestWorkspaceTask,
  fetchWorkspaceTask,
  fetchWorkspaceTasks,
  updateWorkspaceTask,
} from "./api";
import type { WorkspaceTaskSavePayload } from "./types";

export function useWorkspaceTasks() {
  return useQuery({
    queryKey: ["workspace-tasks"],
    queryFn: fetchWorkspaceTasks,
  });
}

export function useLatestWorkspaceTask() {
  return useQuery({
    queryKey: ["workspace-task-latest"],
    queryFn: fetchLatestWorkspaceTask,
  });
}

export function useWorkspaceTask(taskId: number | null) {
  return useQuery({
    queryKey: ["workspace-task", taskId],
    queryFn: () => fetchWorkspaceTask(taskId as number),
    enabled: taskId !== null,
  });
}

export function useCreateWorkspaceTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WorkspaceTaskSavePayload) => createWorkspaceTask(payload),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["workspace-tasks"] });
      void queryClient.setQueryData(["workspace-task", data.id], data);
      void queryClient.setQueryData(["workspace-task-latest"], data);
    },
  });
}

export function useUpdateWorkspaceTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: number; payload: WorkspaceTaskSavePayload }) =>
      updateWorkspaceTask(taskId, payload),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["workspace-tasks"] });
      void queryClient.setQueryData(["workspace-task", data.id], data);
      void queryClient.setQueryData(["workspace-task-latest"], data);
    },
  });
}
