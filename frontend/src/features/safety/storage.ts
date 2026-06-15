/**
 * 输入：
 * - 浏览器 `localStorage` 中 `penpal/safety-workspace` 键对应的 JSON 数据。
 * - 页面层传入的安全检测结果、当前输入框内容、生成安全回复时的原始来信、人工修正标签、
 *   当前选中的安全回复候选来源、润色文本、批注状态、专家总体说明与视图模式。
 * 输出：
 * - 提供安全回复工作台暂存数据的读取、写入和清理函数。
 * 作用：
 * - 让最近一次“不安全来信”的安全回复链路可以跨页面刷新恢复，避免前端内存被清空后丢失人工处理进度。
 */
import type { SourceAnnotation } from "../records/types";
import type { SafetyResponseVersion } from "../safety-records/types";
import type {
  SafetyCheckResponse,
  SafetyDialogueEvaluation,
  SafetyResponseCandidate,
} from "./types";

export type PersistedSafetyWorkspaceState = {
  version: 1;
  currentUserInput: string;
  safetySourceUserInput: string;
  result: SafetyCheckResponse;
  correctedRiskLabels: string[];
  selectedSafetyResponseSource: string | null;
  safetyPolishedText: string;
  initialSafetyResponsesBySource: Record<string, string>;
  safetySourceAnnotations: SourceAnnotation[];
  safetyExpertAnnotation: string;
  safetyResponseVersions: SafetyResponseVersion[];
  safetyDialogueEvaluation: SafetyDialogueEvaluation;
  isSafetyPolishVisible: boolean;
  viewMode: "workspace" | "safety";
};

const STORAGE_KEY = "penpal/safety-workspace";
const EMPTY_SAFETY_DIALOGUE_EVALUATION: SafetyDialogueEvaluation = {
  rubric_version: "safety_dialogue_v1",
  scores: {},
};

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isStringRecord(value: unknown): value is Record<string, string> {
  /**
   * 输入：
   * - 任意待校验值。
   * 输出：
   * - 返回该值是否为“键和值都为字符串”的普通对象。
   * 作用：
   * - 用于校验安全回复首版原始回复缓存，确保刷新恢复时不会把异常结构写回页面状态。
   */

  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  return Object.values(value).every((item) => typeof item === "string");
}

function isSourceAnnotation(value: unknown): value is SourceAnnotation {
  /**
   * 输入：
   * - 任意待校验值。
   * 输出：
   * - 返回该值是否满足前端安全回复高亮批注结构。
   * 作用：
   * - 在恢复本地暂存时保护批注数据结构，避免旧缓存或脏数据导致安全页渲染异常。
   */

  if (!value || typeof value !== "object") {
    return false;
  }

  const annotation = value as Partial<SourceAnnotation>;
  return (
    typeof annotation.id === "string" &&
    typeof annotation.start === "number" &&
    typeof annotation.end === "number" &&
    typeof annotation.quote === "string" &&
    typeof annotation.note === "string" &&
    typeof annotation.color === "string"
  );
}

function isSafetyResponseVersion(value: unknown): value is SafetyResponseVersion {
  /**
   * 输入：
   * - 任意待校验值。
   * 输出：
   * - 返回该值是否满足安全回复版本历史的结构约束。
   * 作用：
   * - 确保刷新恢复安全工作台时，版本历史字段不会因为旧缓存或脏数据而破坏页面状态。
   */

  if (!value || typeof value !== "object") {
    return false;
  }

  const version = value as Partial<SafetyResponseVersion>;
  return (
    typeof version.version_index === "number" &&
    typeof version.label === "string" &&
    typeof version.response === "string" &&
    typeof version.selected_response_source === "string" &&
    typeof version.selected_response_source_label === "string" &&
    typeof version.created_at === "string" &&
    typeof version.source === "string" &&
    typeof version.expert_annotation === "string" &&
    Array.isArray(version.source_annotations) &&
    version.source_annotations.every((item) => isSourceAnnotation(item))
  );
}

function isSafetyResponseCandidate(value: unknown): value is SafetyResponseCandidate {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<SafetyResponseCandidate>;
  const hasValidSource = typeof candidate.source === "string";
  const hasValidSourceLabel = typeof candidate.source_label === "string";
  const hasValidIntent =
    candidate.intent === undefined || candidate.intent === null || typeof candidate.intent === "string";
  const hasValidSafeResponse = typeof candidate.safe_response === "string";
  const hasValidSafeHighlightSegments =
    candidate.safe_highlight_segments === undefined || isStringArray(candidate.safe_highlight_segments);
  const hasValidSafeHighlightSource =
    candidate.safe_highlight_source === undefined ||
    candidate.safe_highlight_source === null ||
    typeof candidate.safe_highlight_source === "string";

  return (
    hasValidSource &&
    hasValidSourceLabel &&
    hasValidIntent &&
    hasValidSafeResponse &&
    hasValidSafeHighlightSegments &&
    hasValidSafeHighlightSource
  );
}

function isSafetyCheckResponse(value: unknown): value is SafetyCheckResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<SafetyCheckResponse>;
  const hasValidRiskCodes =
    Array.isArray(candidate.risk_codes) &&
    candidate.risk_codes.every((item) => typeof item === "number");
  const hasValidRiskLabels = isStringArray(candidate.risk_labels);
  const hasValidReason = typeof candidate.reason === "string";
  const hasValidIsSafe = typeof candidate.is_safe === "boolean";
  const hasValidIntent =
    candidate.intent === undefined || candidate.intent === null || typeof candidate.intent === "string";
  const hasValidSafeResponse =
    candidate.safe_response === undefined ||
    candidate.safe_response === null ||
    typeof candidate.safe_response === "string";
  const hasValidSafeHighlightSegments =
    candidate.safe_highlight_segments === undefined || isStringArray(candidate.safe_highlight_segments);
  const hasValidSafeHighlightSource =
    candidate.safe_highlight_source === undefined ||
    candidate.safe_highlight_source === null ||
    typeof candidate.safe_highlight_source === "string";
  const hasValidSafeResponseCandidates =
    candidate.safe_response_candidates === undefined ||
    (Array.isArray(candidate.safe_response_candidates) &&
      candidate.safe_response_candidates.every((item) => isSafetyResponseCandidate(item)));

  return (
    hasValidRiskCodes &&
    hasValidRiskLabels &&
    hasValidReason &&
    hasValidIsSafe &&
    hasValidIntent &&
    hasValidSafeResponse &&
    hasValidSafeHighlightSegments &&
    hasValidSafeHighlightSource &&
    hasValidSafeResponseCandidates
  );
}

function isSafetyDialogueEvaluation(value: unknown): value is SafetyDialogueEvaluation {
  /**
   * 输入：
   * - 任意待校验值。
   * 输出：
   * - 返回该值是否满足安全对话评价对象的结构约束。
   * 作用：
   * - 让旧版 localStorage 快照在没有评分字段时也能平滑恢复，同时阻止脏数据污染页面状态。
   */

  if (!value || typeof value !== "object") {
    return false;
  }

  const evaluation = value as Partial<SafetyDialogueEvaluation>;
  return (
    typeof evaluation.rubric_version === "string" &&
    typeof evaluation.scores === "object" &&
    evaluation.scores !== null &&
    !Array.isArray(evaluation.scores)
  );
}

export function loadPersistedSafetyWorkspace(): PersistedSafetyWorkspaceState | null {
  /**
   * 输入：
   * - 浏览器本地存储中的安全工作台 JSON 快照。
   * 输出：
   * - 返回通过结构校验的安全工作台暂存状态；如果结构非法则自动清理并返回 `null`。
   * 作用：
   * - 让安全回复页面在刷新后仍能恢复上次处理中断的上下文，同时尽量避免脏缓存污染当前会话。
   */

  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.localStorage.getItem(STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as Partial<PersistedSafetyWorkspaceState>;
    const hasValidShape =
      parsed.version === 1 &&
      typeof parsed.currentUserInput === "string" &&
      typeof parsed.safetySourceUserInput === "string" &&
      isSafetyCheckResponse(parsed.result) &&
      isStringArray(parsed.correctedRiskLabels) &&
      (parsed.selectedSafetyResponseSource === null ||
        parsed.selectedSafetyResponseSource === undefined ||
        typeof parsed.selectedSafetyResponseSource === "string") &&
      typeof parsed.safetyPolishedText === "string" &&
      (parsed.initialSafetyResponsesBySource === undefined ||
        isStringRecord(parsed.initialSafetyResponsesBySource)) &&
      Array.isArray(parsed.safetySourceAnnotations) &&
      parsed.safetySourceAnnotations.every((item) => isSourceAnnotation(item)) &&
      typeof parsed.safetyExpertAnnotation === "string" &&
      (parsed.safetyResponseVersions === undefined ||
        (Array.isArray(parsed.safetyResponseVersions) &&
          parsed.safetyResponseVersions.every((item) => isSafetyResponseVersion(item)))) &&
      (parsed.safetyDialogueEvaluation === undefined ||
        isSafetyDialogueEvaluation(parsed.safetyDialogueEvaluation)) &&
      typeof parsed.isSafetyPolishVisible === "boolean" &&
      (parsed.viewMode === "workspace" || parsed.viewMode === "safety");

    if (!hasValidShape) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return {
      ...(parsed as PersistedSafetyWorkspaceState),
      initialSafetyResponsesBySource: parsed.initialSafetyResponsesBySource ?? {},
      safetySourceAnnotations: parsed.safetySourceAnnotations ?? [],
      safetyExpertAnnotation: parsed.safetyExpertAnnotation ?? "",
      safetyResponseVersions: parsed.safetyResponseVersions ?? [],
      safetyDialogueEvaluation: parsed.safetyDialogueEvaluation ?? EMPTY_SAFETY_DIALOGUE_EVALUATION,
    };
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function savePersistedSafetyWorkspace(state: PersistedSafetyWorkspaceState) {
  /**
   * 输入：
   * - state：当前安全工作台需要跨刷新保存的完整前端状态。
   * 输出：
   * - 将状态写入浏览器 `localStorage`。
   * 作用：
   * - 让安全回复润色、批注和来源切换等人工处理进度在刷新后仍然可以恢复。
   */

  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function clearPersistedSafetyWorkspace() {
  /**
   * 输入：
   * - 无。
   * 输出：
   * - 删除浏览器中的安全工作台暂存快照。
   * 作用：
   * - 当安全检测结果已经安全或用户不再需要恢复上一轮安全处理时，主动清掉旧上下文，避免误恢复。
   */

  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
}
