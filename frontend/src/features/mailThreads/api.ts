import { request } from "../../lib/request";
import type { BatchSessionDetail } from "../records/types";
import type {
  CreateMailMessagePayload,
  CreateMailThreadPayload,
  MailThread,
  MailThreadArchiveResponse,
  MailThreadListResponse,
} from "./types";

export function fetchMailThreads() {
  return request<MailThreadListResponse>("/mail-threads");
}

export function fetchAssignedMailThreads() {
  return request<MailThreadListResponse>("/mail-threads/assigned/mine");
}

export function createMailThread(payload: CreateMailThreadPayload) {
  return request<MailThread>("/mail-threads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function addMailThreadMessage(threadId: number, payload: CreateMailMessagePayload) {
  return request<MailThread>(`/mail-threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function completeMailThread(threadId: number) {
  return request<MailThread>(`/mail-threads/${threadId}/complete`, {
    method: "PATCH",
  });
}

export function archiveAiReplyToRecords(threadId: number) {
  return request<MailThreadArchiveResponse>(`/mail-threads/${threadId}/archive-ai-reply`, {
    method: "POST",
  });
}

export function unarchiveAiReplyFromRecords(threadId: number) {
  return request<MailThreadArchiveResponse>(`/mail-threads/${threadId}/archive-ai-reply`, {
    method: "DELETE",
  });
}

export function submitCounselorThreadReply(threadId: number, content: string) {
  return request<MailThread>(`/mail-threads/assigned/${threadId}/reply`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function createAssignedThreadWorkspaceSession(threadId: number) {
  return request<BatchSessionDetail>(`/mail-threads/assigned/${threadId}/workspace-session`, {
    method: "POST",
  });
}

export function createAssignedThreadsWorkspaceSession() {
  return request<BatchSessionDetail>("/mail-threads/assigned/workspace-session", {
    method: "POST",
  });
}
