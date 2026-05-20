import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  exportBatchGeneration,
  exportRecordsExcel,
  exportReviewedBatch,
  fetchBatchSession,
  fetchBatchSessions,
  fetchRecord,
  fetchRecords,
  importBatchExcel,
  regenerateBatchSessionItem,
  rollbackBatchSessionItem,
  saveRecord,
  updateBatchSessionItem,
} from "./api";
import type {
  BatchExcelItem,
  BatchSessionItemRegeneratePayload,
  BatchSessionItemUpdatePayload,
  ReviewedBatchItem,
  SaveRecordPayload,
} from "./types";

export function useRecords(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["records", page, pageSize],
    queryFn: () => fetchRecords(page, pageSize),
  });
}

export function useRecord(recordId: number | null) {
  return useQuery({
    queryKey: ["record", recordId],
    queryFn: () => fetchRecord(recordId as number),
    enabled: recordId !== null,
  });
}

export function useSaveRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SaveRecordPayload) => saveRecord(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["records"] });
    },
  });
}

export function useImportBatchExcel() {
  return useMutation({
    mutationFn: (file: File) => importBatchExcel(file),
  });
}

export function useBatchSessions() {
  return useQuery({
    queryKey: ["batch-sessions"],
    queryFn: fetchBatchSessions,
  });
}

export function useBatchSession(sessionId: number | null) {
  return useQuery({
    queryKey: ["batch-session", sessionId],
    queryFn: () => fetchBatchSession(sessionId as number),
    enabled: sessionId !== null,
  });
}

export function useUpdateBatchSessionItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      itemId,
      payload,
    }: {
      sessionId: number;
      itemId: number;
      payload: BatchSessionItemUpdatePayload;
    }) => updateBatchSessionItem(sessionId, itemId, payload),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["batch-sessions"] });
      void queryClient.setQueryData(["batch-session", data.id], data);
    },
  });
}

export function useRegenerateBatchSessionItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      itemId,
      payload,
    }: {
      sessionId: number;
      itemId: number;
      payload: BatchSessionItemRegeneratePayload;
    }) => regenerateBatchSessionItem(sessionId, itemId, payload),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["batch-sessions"] });
      void queryClient.setQueryData(["batch-session", data.id], data);
    },
  });
}

export function useRollbackBatchSessionItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      itemId,
      versionIndex,
    }: {
      sessionId: number;
      itemId: number;
      versionIndex: number;
    }) => rollbackBatchSessionItem(sessionId, itemId, versionIndex),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["batch-sessions"] });
      void queryClient.setQueryData(["batch-session", data.id], data);
    },
  });
}

export function useExportBatchGeneration() {
  return useMutation({
    mutationFn: (items: BatchExcelItem[]) => exportBatchGeneration(items),
  });
}

export function useExportRecordsExcel() {
  return useMutation({
    mutationFn: () => exportRecordsExcel(),
  });
}

export function useExportReviewedBatch() {
  return useMutation({
    mutationFn: (items: ReviewedBatchItem[]) => exportReviewedBatch(items),
  });
}
