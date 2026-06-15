/**
 * 输入：
 * - 安全回复记录接口的保存请求、列表结果和详情结果。
 * 输出：
 * - 导出安全回复记录相关的 TypeScript 类型。
 * 作用：
 * - 为安全回复记录的保存、列表和详情展示提供统一类型约束。
 */
import type { SourceAnnotation } from "../records/types";
import type { SafetyDialogueEvaluation, SafetyResponseCandidate } from "../safety/types";

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
  selected_response_source: string;
  selected_response_source_label: string;
  safe_response_candidates_json: SafetyResponseCandidate[];
  expert_annotation: string;
  sample_snapshot_json: Record<string, unknown>;
  safety_evaluation?: SafetyDialogueEvaluation;
  source_annotations_json: SourceAnnotation[];
  response_versions_json: SafetyResponseVersion[];
  created_at: string;
  updated_at: string;
};

export type SafetyResponseVersion = {
  version_index: number;
  label: string;
  response: string;
  selected_response_source: string;
  selected_response_source_label: string;
  created_at: string;
  source: string;
  expert_annotation: string;
  source_annotations: SourceAnnotation[];
};

export type SaveSafetyRecordPayload = {
  user_input: string;
  risk_labels: string[];
  corrected_risk_labels: string[];
  risk_reason: string;
  ai_safe_response: string;
  expert_polished_response: string;
  selected_response_source?: string;
  selected_response_source_label?: string;
  safe_response_candidates?: SafetyResponseCandidate[];
  expert_annotation?: string;
  safety_evaluation?: SafetyDialogueEvaluation;
  sample_snapshot?: Record<string, unknown>;
  source_annotations?: SourceAnnotation[];
  response_versions?: SafetyResponseVersion[];
};
