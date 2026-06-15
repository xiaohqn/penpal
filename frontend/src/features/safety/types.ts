/**
 * 输入：
 * - 安全检测接口的请求参数，以及接口返回的风险判断、安全回复、高亮片段、高亮来源，
 *   对比模式下的多份安全回复候选，以及安全回复专家批注重生成所需的请求体。
 * 输出：
 * - 导出安全检测链路与安全回复批注重生成链路所需的 TypeScript 类型。
 * 作用：
 * - 让请求层、状态层、页面层和本地持久化层对安全回复相关数据保持一致认知，
 *   避免新增的批注重生成字段只在某一层被感知。
 */
import type { SourceAnnotation } from "../records/types";

export type SafetyDialogueEvaluationScores = {
  risk_response_and_emergency_handling?: number;
  supportive_nonjudgmental_attitude?: number;
  authentic_companionship?: number;
  human_presence_and_deep_empathy?: number;
};

export type SafetyDialogueEvaluation = {
  rubric_version: string;
  scores: SafetyDialogueEvaluationScores;
  total_score?: number;
  average_score?: number;
};

export type SafetyCheckRequest = {
  user_input: string;
  source_mode?: "auto" | "api" | "vllm" | "compare";
};

export type SafetyResponseCandidate = {
  source: string;
  source_label: string;
  intent?: string | null;
  safe_response: string;
  safe_highlight_segments?: string[];
  safe_highlight_source?: string | null;
};

export type SafetyRegenerateRequest = {
  user_input: string;
  risk_codes: number[];
  corrected_risk_labels: string[];
  risk_reason: string;
  source: "api" | "local" | "mock";
  current_response: string;
  source_annotations: SourceAnnotation[];
  expert_annotation: string;
  safety_evaluation?: SafetyDialogueEvaluation;
};

export type SafetyCheckResponse = {
  risk_codes: number[];
  risk_labels: string[];
  reason: string;
  is_safe: boolean;
  intent?: string | null;
  safe_response?: string | null;
  safe_highlight_segments?: string[];
  safe_highlight_source?: string | null;
  safe_response_candidates?: SafetyResponseCandidate[];
};

export type SafetyState =
  | {
      status: "idle";
      result: null;
      error: null;
    }
  | {
      status: "loading";
      result: null;
      error: null;
    }
  | {
      status: "success";
      result: SafetyCheckResponse;
      error: null;
    }
  | {
      status: "error";
      result: null;
      error: string;
    };
