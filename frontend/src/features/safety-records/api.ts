/**
 * 输入：
 * - 安全回复记录查询所需的分页参数、记录 ID，以及保存、删除、导出动作对应的参数。
 * 输出：
 * - 提供安全回复记录列表、详情、保存、删除和导出请求函数。
 * 作用：
 * - 集中封装前端对 `/safety-records` 接口的访问。
 */
import { buildApiUrl } from "../../lib/api-base";
import { request } from "../../lib/request";
import type {
  SafetyRecordDetail,
  SafetyRecordListResponse,
  SaveSafetyRecordPayload,
} from "./types";

export function fetchSafetyRecords(page = 1, pageSize = 10) {
  return request<SafetyRecordListResponse>(`/safety-records?page=${page}&page_size=${pageSize}`);
}

export function fetchSafetyRecord(recordId: number) {
  return request<SafetyRecordDetail>(`/safety-records/${recordId}`);
}

export function saveSafetyRecord(payload: SaveSafetyRecordPayload) {
  return request<SafetyRecordDetail>("/safety-records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteSafetyRecord(recordId: number) {
  return request<void>(`/safety-records/${recordId}`, {
    method: "DELETE",
  });
}

export async function exportSafetyRecordsExcel() {
  /**
   * 输入：
   * - 无；默认导出全部安全回复历史记录。
   * 输出：
   * - 返回后端导出的安全回复记录 Excel 二进制数据。
   * 作用：
   * - 为历史页安全回复记录导出按钮提供独立的数据下载入口。
   */

  const response = await fetch(buildApiUrl("/api/v1/safety-records/export"));
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.blob();
}
