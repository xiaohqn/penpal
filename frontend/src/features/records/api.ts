import { buildApiUrl } from "../../lib/api-base";
import { getAuthHeaders, getStoredCounselorId } from "../../app/auth";
import { request } from "../../lib/request";
import type {
  BatchExcelImportResponse,
  BatchExcelItem,
  BatchSessionDetail,
  BatchSessionItemRegeneratePayload,
  BatchSessionItemUpdatePayload,
  BatchSessionListResponse,
  RecordDetail,
  RecordListResponse,
  ReviewedBatchItem,
  SaveRecordPayload,
  UpdateRecordPayload,
} from "./types";

export function fetchRecords(page = 1, pageSize = 10, scope: "mine" | "all" = "mine") {
  return request<RecordListResponse>(`/records?page=${page}&page_size=${pageSize}&scope=${scope}`);
}

export function fetchRecord(recordId: number, scope: "mine" | "all" = "mine") {
  return request<RecordDetail>(`/records/${recordId}?scope=${scope}`);
}

export function saveRecord(payload: SaveRecordPayload) {
  return request<RecordDetail>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRecord(recordId: number, payload: UpdateRecordPayload, scope: "mine" | "all" = "mine") {
  return request<RecordDetail>(`/records/${recordId}?scope=${scope}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function importBatchExcel(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(buildApiUrl("/api/v1/batch/import"), {
    method: "POST",
    headers: {
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<BatchSessionDetail>;
}

export async function exportBatchGeneration(items: BatchExcelItem[]) {
  const response = await fetch(buildApiUrl("/api/v1/batch/generate/export"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ items }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.blob();
}

export async function exportRecordsExcel(scope: "mine" | "all" = "mine") {
  const response = await fetch(buildApiUrl(`/api/v1/batch/records/export?scope=${scope}`), {
    headers: {
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.blob();
}

export async function exportReviewedBatch(items: ReviewedBatchItem[]) {
  const response = await fetch(buildApiUrl("/api/v1/batch/reviewed/export"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ items }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.blob();
}

export function fetchBatchSessions() {
  return request<BatchSessionListResponse>("/batch/sessions");
}

export function fetchBatchSession(sessionId: number) {
  return request<BatchSessionDetail>(`/batch/sessions/${sessionId}`);
}

export function setCurrentBatchSessionItem(sessionId: number, itemId: number) {
  return request<BatchSessionDetail>(`/batch/sessions/${sessionId}/items/${itemId}/current`, {
    method: "PATCH",
  });
}

export async function updateBatchSessionItem(
  sessionId: number,
  itemId: number,
  payload: BatchSessionItemUpdatePayload,
) {
  const response = await fetch(buildApiUrl(`/api/v1/batch/sessions/${sessionId}/items/${itemId}`), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<BatchSessionDetail>;
}

export async function regenerateBatchSessionItem(
  sessionId: number,
  itemId: number,
  payload: BatchSessionItemRegeneratePayload,
) {
  const response = await fetch(buildApiUrl(`/api/v1/batch/sessions/${sessionId}/items/${itemId}/regenerate`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<BatchSessionDetail>;
}

export async function rollbackBatchSessionItem(
  sessionId: number,
  itemId: number,
  versionIndex: number,
) {
  const response = await fetch(buildApiUrl(`/api/v1/batch/sessions/${sessionId}/items/${itemId}/rollback`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Counselor-Id": getStoredCounselorId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ version_index: versionIndex }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<BatchSessionDetail>;
}
