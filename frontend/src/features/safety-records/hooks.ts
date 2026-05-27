/**
 * 输入：
 * - 安全回复记录的分页参数、记录 ID，以及保存、删除或导出动作的参数。
 * 输出：
 * - 返回安全回复记录的列表查询、详情查询、保存 / 删除 / 导出 mutation hooks。
 * 作用：
 * - 用 React Query 管理安全回复记录的数据访问、缓存刷新与文件导出动作。
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteSafetyRecord,
  exportSafetyRecordsExcel,
  fetchSafetyRecord,
  fetchSafetyRecords,
  saveSafetyRecord,
} from "./api";
import type { SaveSafetyRecordPayload } from "./types";

export function useSafetyRecords(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["safety-records", page, pageSize],
    queryFn: () => fetchSafetyRecords(page, pageSize),
  });
}

export function useSafetyRecord(recordId: number | null) {
  return useQuery({
    queryKey: ["safety-record", recordId],
    queryFn: () => fetchSafetyRecord(recordId as number),
    enabled: recordId !== null,
  });
}

export function useSaveSafetyRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SaveSafetyRecordPayload) => saveSafetyRecord(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["safety-records"] });
    },
  });
}

export function useDeleteSafetyRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recordId: number) => deleteSafetyRecord(recordId),
    onSuccess: (_data, recordId) => {
      void queryClient.invalidateQueries({ queryKey: ["safety-records"] });
      queryClient.removeQueries({ queryKey: ["safety-record", recordId] });
    },
  });
}

export function useExportSafetyRecordsExcel() {
  /**
   * 输入：
   * - 无；调用时直接导出当前安全回复样本库全部记录。
   * 输出：
   * - 返回一个导出安全回复记录 Excel 的 mutation。
   * 作用：
   * - 让历史页在切到安全回复记录时，也能复用统一的文件导出触发方式。
   */

  return useMutation({
    mutationFn: () => exportSafetyRecordsExcel(),
  });
}
