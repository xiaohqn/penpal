/**
 * 输入：
 * - 安全回复记录接口的保存请求、列表结果和详情结果。
 * 输出：
 * - 导出安全回复记录相关的 TypeScript 类型。
 * 作用：
 * - 为安全回复记录的保存、列表和详情展示提供统一类型约束。
 */
export type SafetyRecordItem = {
  id: number;
  style_name: string;
  user_input: string;
  created_at: string;
  updated_at: string;
};

export type SafetyRecordListResponse = {
  items: SafetyRecordItem[];
  total: number;
  page: number;
  page_size: number;
};

export type SafetyRecordDetail = {
  id: number;
  style_name: string;
  user_input: string;
  risk_labels_json: string[];
  corrected_risk_labels_json: string[];
  risk_reason: string;
  ai_safe_response: string;
  expert_polished_response: string;
  created_at: string;
  updated_at: string;
};

export type SaveSafetyRecordPayload = {
  user_input: string;
  risk_labels: string[];
  corrected_risk_labels: string[];
  risk_reason: string;
  ai_safe_response: string;
  expert_polished_response: string;
};
