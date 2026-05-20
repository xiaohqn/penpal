import { buildApiUrl } from "../../lib/api-base";
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
} from "./types";

export function fetchRecords(page = 1, pageSize = 10) {
  return request<RecordListResponse>(`/records?page=${page}&page_size=${pageSize}`);
}

export function fetchRecord(recordId: number) {
  return request<RecordDetail>(`/records/${recordId}`);
}

export function saveRecord(payload: SaveRecordPayload) {
  return request<RecordDetail>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function importBatchExcel(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(buildApiUrl("/api/v1/batch/import"), {
    method: "POST",
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
    },
    body: JSON.stringify({ items }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.blob();
}

export async function exportRecordsExcel() {
  const response = await fetch(buildApiUrl("/api/v1/batch/records/export"));
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

export async function updateBatchSessionItem(
  sessionId: number,
  itemId: number,
  payload: BatchSessionItemUpdatePayload,
) {
  const response = await fetch(buildApiUrl(`/api/v1/batch/sessions/${sessionId}/items/${itemId}`), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
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
    },
    body: JSON.stringify({ version_index: versionIndex }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<BatchSessionDetail>;
}
