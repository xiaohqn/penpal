import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addMailThreadMessage,
  archiveAiReplyToRecords,
  completeMailThread,
  createMailThread,
  createAssignedThreadWorkspaceSession,
  createAssignedThreadsWorkspaceSession,
  fetchAssignedMailThreads,
  fetchMailThreads,
  submitCounselorThreadReply,
  unarchiveAiReplyFromRecords,
} from "./api";
import type { CreateMailMessagePayload, CreateMailThreadPayload } from "./types";

export function useMailThreads() {
  return useQuery({
    queryKey: ["mail-threads"],
    queryFn: fetchMailThreads,
  });
}

export function useAssignedMailThreads() {
  return useQuery({
    queryKey: ["assigned-mail-threads"],
    queryFn: fetchAssignedMailThreads,
  });
}

export function useCreateMailThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateMailThreadPayload) => createMailThread(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mail-threads"] });
    },
  });
}

export function useAddMailThreadMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ threadId, payload }: { threadId: number; payload: CreateMailMessagePayload }) =>
      addMailThreadMessage(threadId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mail-threads"] });
    },
  });
}

export function useCompleteMailThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (threadId: number) => completeMailThread(threadId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mail-threads"] });
    },
  });
}

export function useArchiveAiReplyToRecords() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (threadId: number) => archiveAiReplyToRecords(threadId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mail-threads"] });
      void queryClient.invalidateQueries({ queryKey: ["records"] });
    },
  });
}

export function useUnarchiveAiReplyFromRecords() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (threadId: number) => unarchiveAiReplyFromRecords(threadId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mail-threads"] });
      void queryClient.invalidateQueries({ queryKey: ["records"] });
    },
  });
}

export function useSubmitCounselorThreadReply() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ threadId, content }: { threadId: number; content: string }) =>
      submitCounselorThreadReply(threadId, content),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assigned-mail-threads"] });
    },
  });
}

export function useCreateAssignedThreadWorkspaceSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (threadId: number) => createAssignedThreadWorkspaceSession(threadId),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["batch-sessions"] });
      void queryClient.setQueryData(["batch-session", data.id], data);
    },
  });
}

export function useCreateAssignedThreadsWorkspaceSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAssignedThreadsWorkspaceSession,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["batch-sessions"] });
      void queryClient.setQueryData(["batch-session", data.id], data);
    },
  });
}
