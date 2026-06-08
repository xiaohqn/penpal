/**
 * 输入：
 * - 人格目录接口、生成接口、记录保存接口、安全检测接口与批量处理接口返回的数据。
 * - 用户输入的来信正文、选中的人格列表、批量任务状态，以及安全回复相关的人工修正状态。
 * 输出：
 * - 渲染完整工作台页面，包括常规草稿工作流、批量处理工作流和不安全时的安全回复结果页。
 * - 维护草稿、版本、批注、润色文本、保存提示，以及安全检测后的视图切换状态、
 *   安全回复候选切换状态、安全回复人工润色状态与安全回复批注重生成状态。
 * 作用：
 * - 这是前端主页面的编排层，负责把普通生成流程、批量处理流程和安全兜底流程整合到同一套交互里。
 */
import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { RefreshCcw, ScrollText, Sparkles } from "lucide-react";

import { BatchExcelPanel } from "../components/BatchExcelPanel";
import { DraftStreamTabs } from "../components/DraftStreamTabs";
import { ExpertAnnotationPanel } from "../components/ExpertAnnotationPanel";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { PersonaSelector } from "../components/PersonaSelector";
import { PlannerInsightAccordion } from "../components/PlannerInsightAccordion";
import { PolishingEditor } from "../components/PolishingEditor";
import {
  EMPTY_EVALUATION,
  normalizeResponseEvaluation,
  ResponseEvaluationPanel,
} from "../components/ResponseEvaluationPanel";
import { ResponseVersionPanel } from "../components/ResponseVersionPanel";
import { SafetyCheckBar } from "../components/SafetyCheckBar";
import { SafetyResultPanel } from "../components/SafetyResultPanel";
import { SaveRecordBar } from "../components/SaveRecordBar";
import { ToneGuideBar } from "../components/ToneGuideBar";
import { UserLetterPanel } from "../components/UserLetterPanel";
import { useGenerationWorkspace, usePersonas } from "../features/generation/hooks";
import type { DraftCandidate, PlannerOutput } from "../features/generation/types";
import {
  useBatchSession,
  useBatchSessions,
  useExportReviewedBatch,
  useImportBatchExcel,
  useRegenerateBatchSessionItem,
  useRollbackBatchSessionItem,
  useSaveRecord,
  useUpdateBatchSessionItem,
} from "../features/records/hooks";
import { useSaveSafetyRecord } from "../features/safety-records/hooks";
import { useRegenerateSafetyReply, useSafetyCheck } from "../features/safety/hooks";
import {
  clearPersistedSafetyWorkspace,
  loadPersistedSafetyWorkspace,
  savePersistedSafetyWorkspace,
} from "../features/safety/storage";
import type {
  SafetyCheckResponse,
  SafetyRegenerateRequest,
  SafetyResponseCandidate,
} from "../features/safety/types";
import type {
  BatchSessionItem,
  ResponseVersion,
  ResponseEvaluation,
  ReviewedBatchItem,
  SourceAnnotation,
} from "../features/records/types";

const DEFAULT_INPUT = `这段时间我过得特别难受。每天早上想到要去学校，心里就沉甸甸的，很害怕。我不是不想学习，但上课时总控制不住地分心，总担心同学在背后议论我。放学我也尽量绕路，躲开那几个经常堵我的同学。

这些事压得我快喘不过气了。我试过想跟爸妈或者别人说，但话到嘴边又说不出来，怕没人信，也怕情况变得更糟。现在晚上经常失眠，躲在被子里哭，白天还要强撑着，感觉特别累，好像下一秒就要垮掉。

我真的不知道该怎么办了，感觉自己快扛不住了。您能给我一点建议吗？`;
type WorkspaceViewMode = "workspace" | "safety";

function buildInitialSafetyResponseMap(result: SafetyCheckResponse): Record<string, string> {
  /**
   * 输入：
   * - result：当前安全检测成功后的完整响应。
   * 输出：
   * - 返回按候选来源分组的“首版安全回复”缓存映射。
   * 作用：
   * - 让安全回复页在后续批注重生成、候选切换和保存记录时，都还能拿到每条来源候选最开始那版原始回复。
   */

  const candidates = result.safe_response_candidates ?? [];
  if (candidates.length === 0) {
    return {};
  }

  return candidates.reduce<Record<string, string>>((accumulator, candidate) => {
    if (candidate.source && candidate.safe_response && !accumulator[candidate.source]) {
      accumulator[candidate.source] = candidate.safe_response;
    }
    return accumulator;
  }, {});
}

function buildReviewedItems(items: BatchSessionItem[]): ReviewedBatchItem[] {
  return items
    .filter((item) => item.status === "completed")
    .map((item) => ({
      item_id: item.id,
      row_number: item.row_number,
      user_input: item.user_input,
      selected_persona_name: item.selected_persona_name,
      final_response: item.latest_response,
      expert_annotation: item.expert_annotation,
      rag_ready: item.rag_ready,
      sample_reason: item.sample_reason,
      source_annotations: item.source_annotations_json,
      evaluation: (item.evaluation_json as ResponseEvaluation) ?? EMPTY_EVALUATION,
      active_version_index: item.active_version_index,
    }))
    .sort((a, b) => a.row_number - b.row_number);
}

function getActiveSafetyResponseCandidate(
  result: SafetyCheckResponse | null | undefined,
  selectedSource: string | null,
): SafetyResponseCandidate | null {
  const candidates = result?.safe_response_candidates ?? [];
  if (candidates.length === 0) {
    return null;
  }

  if (selectedSource) {
    const matchedCandidate = candidates.find((candidate) => candidate.source === selectedSource);
    if (matchedCandidate) {
      return matchedCandidate;
    }
  }

  return candidates[0] ?? null;
}

export function WorkspacePage() {
  const [persistedSafetySnapshot] = useState(() => loadPersistedSafetyWorkspace());
  const { data, isLoading } = usePersonas();
  const batchSessions = useBatchSessions();
  const {
    drafts,
    activeDraft,
    selectedPersona,
    setSelectedPersona,
    jobLoading,
    jobError,
    startGeneration,
    generateDraftFromPlan,
    updateDraftPlanner,
    resetWorkspace,
    hydrateWorkspace,
  } = useGenerationWorkspace();
  const saveRecord = useSaveRecord();
  const saveSafetyRecord = useSaveSafetyRecord();
  const regenerateSafetyReply = useRegenerateSafetyReply();
  const importBatchExcel = useImportBatchExcel();
  const updateBatchSessionItem = useUpdateBatchSessionItem();
  const regenerateBatchSessionItem = useRegenerateBatchSessionItem();
  const rollbackBatchSessionItem = useRollbackBatchSessionItem();
  const exportReviewedBatch = useExportReviewedBatch();
  const { state: safetyState, runSafetyCheck, replaceSafetyResult, isChecking } = useSafetyCheck(
    persistedSafetySnapshot
      ? {
          status: "success",
          result: persistedSafetySnapshot.result,
          error: null,
        }
      : undefined,
  );

  const personas = data?.personas ?? [];
  const availableSessions = batchSessions.data?.items ?? [];

  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const batchSession = useBatchSession(activeSessionId);
  const sessionDetail = batchSession.data;

  const batchItems = useMemo(
    () =>
      (sessionDetail?.items ?? []).map((item) => ({
        id: item.id,
        session_id: item.session_id,
        row_number: item.row_number,
        user_input: item.user_input,
        selected_persona_names: item.selected_persona_names_json,
        selected_persona_name: item.selected_persona_name,
        selected_style_config_json: item.selected_style_config_json,
        planner_output_json: item.planner_output_json,
        draft_candidates_json: item.draft_candidates_json,
        ai_selected_raw_response: item.ai_selected_raw_response,
        latest_response: item.latest_response,
        expert_annotation: item.expert_annotation,
        rag_ready: item.rag_ready,
        sample_reason: item.sample_reason,
        sample_snapshot_json: item.sample_snapshot_json,
        evaluation_json: item.evaluation_json,
        source_annotations_json: item.source_annotations_json,
        response_versions_json: item.response_versions_json,
        active_version_index: item.active_version_index,
        status: item.status,
        record_id: item.record_id,
      })),
    [sessionDetail?.items],
  );

  const [userInput, setUserInput] = useState(
    persistedSafetySnapshot?.currentUserInput ?? DEFAULT_INPUT,
  );
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>([]);
  const [polishedText, setPolishedText] = useState("");
  const [expertAnnotation, setExpertAnnotation] = useState("");
  const [sampleReason, setSampleReason] = useState("");
  const [statusText, setStatusText] = useState<string | null>(null);
  const [safetyStatusText, setSafetyStatusText] = useState<string | null>(null);
  const [safetySaveStatusText, setSafetySaveStatusText] = useState<string | null>(null);
  const [safetyRegenerateStatusText, setSafetyRegenerateStatusText] = useState<string | null>(null);
  const [batchFileName, setBatchFileName] = useState<string | null>(null);
  const [batchCurrentIndex, setBatchCurrentIndex] = useState(0);
  const [workspaceMode, setWorkspaceMode] = useState<"single" | "batch">("single");
  const [viewMode, setViewMode] = useState<WorkspaceViewMode>(
    persistedSafetySnapshot?.viewMode ?? "workspace",
  );
  const [generationSourceMode, setGenerationSourceMode] = useState<"auto" | "api" | "vllm" | "compare">("compare");
  const [rightPanelMode, setRightPanelMode] = useState<"batch" | "evaluation">("batch");
  const [sourceAnnotations, setSourceAnnotations] = useState<SourceAnnotation[]>([]);
  const [responseVersions, setResponseVersions] = useState<ResponseVersion[]>([]);
  const [responseEvaluation, setResponseEvaluation] = useState<ResponseEvaluation>(EMPTY_EVALUATION);
  const [activeVersionIndex, setActiveVersionIndex] = useState(0);
  const [initialDraftResponses, setInitialDraftResponses] = useState<Record<string, string>>({});
  const [correctedRiskLabels, setCorrectedRiskLabels] = useState<string[]>(
    persistedSafetySnapshot?.correctedRiskLabels.length
      ? persistedSafetySnapshot.correctedRiskLabels
      : persistedSafetySnapshot?.result.risk_labels ?? [],
  );
  const [selectedSafetyResponseSource, setSelectedSafetyResponseSource] = useState<string | null>(
    persistedSafetySnapshot?.selectedSafetyResponseSource ?? null,
  );
  const [safetyPolishedText, setSafetyPolishedText] = useState(
    persistedSafetySnapshot?.safetyPolishedText ?? "",
  );
  const [initialSafetyResponsesBySource, setInitialSafetyResponsesBySource] = useState<Record<string, string>>(
    persistedSafetySnapshot?.initialSafetyResponsesBySource ?? {},
  );
  const [safetySourceAnnotations, setSafetySourceAnnotations] = useState<SourceAnnotation[]>(
    persistedSafetySnapshot?.safetySourceAnnotations ?? [],
  );
  const [safetyExpertAnnotation, setSafetyExpertAnnotation] = useState(
    persistedSafetySnapshot?.safetyExpertAnnotation ?? "",
  );
  const [isSafetyPolishVisible, setIsSafetyPolishVisible] = useState(
    persistedSafetySnapshot?.isSafetyPolishVisible ?? false,
  );
  const [safetySourceUserInput, setSafetySourceUserInput] = useState(
    persistedSafetySnapshot?.safetySourceUserInput ?? "",
  );
  const [lastHydratedDraft, setLastHydratedDraft] = useState<{
    personaName: string | null;
    response: string;
  }>({
    personaName: null,
    response: "",
  });

  const isBatchMode = batchItems.length > 0;
  const isWorkspaceBatchMode = workspaceMode === "batch";
  const currentBatchItem = isBatchMode ? batchItems[batchCurrentIndex] ?? null : null;
  const activeBatchItem = isWorkspaceBatchMode ? currentBatchItem : null;
  const batchCompletedCount = batchItems.filter((item) => item.status === "completed").length;
  const batchAllCompleted = isBatchMode && batchCompletedCount === batchItems.length;
  const completedRowNumbers = batchItems.filter((item) => item.status === "completed").map((item) => item.row_number);
  const reviewedBatchItems = buildReviewedItems(sessionDetail?.items ?? []);
  const hasUnsafeSafetyResult =
    safetyState.status === "success" &&
    Boolean(safetyState.result) &&
    !safetyState.result.is_safe;
  const activeSafetyCandidate = getActiveSafetyResponseCandidate(
    safetyState.status === "success" ? safetyState.result : null,
    selectedSafetyResponseSource,
  );

  useEffect(() => {
    if (safetyState.status !== "success") {
      return;
    }

    if (safetyState.result.is_safe) {
      clearPersistedSafetyWorkspace();
      return;
    }

    savePersistedSafetyWorkspace({
      version: 1,
      currentUserInput: userInput,
      safetySourceUserInput: safetySourceUserInput || userInput,
      result: safetyState.result,
      correctedRiskLabels:
        correctedRiskLabels.length > 0 ? correctedRiskLabels : safetyState.result.risk_labels,
      selectedSafetyResponseSource,
      safetyPolishedText: safetyPolishedText || safetyState.result.safe_response || "",
      initialSafetyResponsesBySource,
      safetySourceAnnotations,
      safetyExpertAnnotation,
      isSafetyPolishVisible,
      viewMode,
    });
  }, [
    correctedRiskLabels,
    initialSafetyResponsesBySource,
    isSafetyPolishVisible,
    safetyExpertAnnotation,
    safetySourceAnnotations,
    selectedSafetyResponseSource,
    safetyPolishedText,
    safetySourceUserInput,
    safetyState.result,
    safetyState.status,
    userInput,
    viewMode,
  ]);

  useEffect(() => {
    if (activeSessionId !== null) {
      return;
    }
    const inProgress = availableSessions.find((session) => session.status !== "completed");
    const fallback = availableSessions[0] ?? null;
    const nextSession = inProgress ?? fallback;
    if (nextSession) {
      setActiveSessionId(nextSession.id);
    }
  }, [activeSessionId, availableSessions]);

  useEffect(() => {
    if (!isBatchMode && personas.length > 0 && selectedPersonas.length === 0) {
      setSelectedPersonas(personas.slice(0, 3).map((item) => item.name));
    }
  }, [isBatchMode, personas, selectedPersonas.length]);

  useEffect(() => {
    if (!sessionDetail?.items?.length) {
      return;
    }
    const nextIndex = Math.max(
      0,
      sessionDetail.items.findIndex((item) => item.id === sessionDetail.current_item_id),
    );
    setBatchCurrentIndex(nextIndex >= 0 ? nextIndex : 0);
    setBatchFileName(sessionDetail.source_file_name || sessionDetail.title);
  }, [sessionDetail?.current_item_id, sessionDetail?.items, sessionDetail?.source_file_name, sessionDetail?.title]);

  useEffect(() => {
    if (!activeBatchItem || !isWorkspaceBatchMode) {
      return;
    }

    resetWorkspace();
    setInitialDraftResponses({});
    setUserInput(activeBatchItem.user_input);
    setSelectedPersonas(activeBatchItem.selected_persona_names ?? []);
    setSourceAnnotations(activeBatchItem.source_annotations_json ?? []);
    setResponseVersions(activeBatchItem.response_versions_json ?? []);
    setActiveVersionIndex(activeBatchItem.active_version_index ?? 0);
    setExpertAnnotation(activeBatchItem.expert_annotation ?? "");
    setSampleReason(activeBatchItem.sample_reason ?? "");
    setResponseEvaluation(
      normalizeResponseEvaluation((activeBatchItem.evaluation_json as ResponseEvaluation) ?? EMPTY_EVALUATION),
    );
    setPolishedText(activeBatchItem.latest_response ?? "");
    setStatusText(
      activeBatchItem.status === "completed"
        ? `已恢复第 ${batchCurrentIndex + 1} / ${batchItems.length} 条，当前为已完成状态，可回看版本或继续修改。`
        : `已恢复第 ${batchCurrentIndex + 1} / ${batchItems.length} 条，请继续处理。`,
    );

    if (activeBatchItem.draft_candidates_json?.length) {
      const nextInitialDraftResponses = activeBatchItem.draft_candidates_json.reduce<Record<string, string>>(
        (accumulator, draft) => {
          const draftId = String(
            draft.draft_id ?? `${String(draft.persona_name ?? "")}::${String(draft.source ?? "api")}`,
          );
          const candidateOriginal = String(draft.raw_response ?? draft.response ?? "").trim();
          if (candidateOriginal) {
            accumulator[draftId] = candidateOriginal;
          }
          return accumulator;
        },
        {},
      );
      if (activeBatchItem.ai_selected_raw_response?.trim()) {
        const selectedDraftId =
          String(activeBatchItem.draft_candidates_json[0]?.draft_id ?? "") ||
          activeBatchItem.selected_persona_name ||
          activeBatchItem.selected_persona_names?.[0] ||
          "";
        if (selectedDraftId) {
          nextInitialDraftResponses[selectedDraftId] = activeBatchItem.ai_selected_raw_response.trim();
        }
      }
      setInitialDraftResponses(nextInitialDraftResponses);
      hydrateWorkspace({
        drafts: activeBatchItem.draft_candidates_json.map((draft) => ({
          draft_id: String(draft.draft_id ?? `${String(draft.persona_name ?? "")}::${String(draft.source ?? "api")}`),
          persona_name: String(draft.persona_name ?? ""),
          source: String(draft.source ?? "api"),
          source_label: String(draft.source_label ?? "API 模型"),
          style_config: (draft.style_config ?? {}) as Record<string, string>,
          planner_output: (draft.planner_output ?? {}) as Record<string, unknown>,
          response: String(draft.response ?? ""),
          raw_response: String(draft.raw_response ?? ""),
        })),
        selectedPersona:
          String(activeBatchItem.draft_candidates_json[0]?.draft_id ?? "") ||
          activeBatchItem.selected_persona_name ||
          activeBatchItem.selected_persona_names?.[0] ||
          null,
      });
    }
  }, [activeBatchItem, batchCurrentIndex, batchItems, hydrateWorkspace, isWorkspaceBatchMode, resetWorkspace]);

  useEffect(() => {
    if (!activeDraft?.response) {
      return;
    }

    const personaChanged = lastHydratedDraft.personaName !== activeDraft.persona_name;
    const editorStillMatchesLastHydrated = polishedText === lastHydratedDraft.response;

    if (personaChanged || !polishedText.trim() || editorStillMatchesLastHydrated) {
      setPolishedText(activeDraft.response);
      setLastHydratedDraft({
        personaName: activeDraft.persona_name,
        response: activeDraft.response,
      });
    }
  }, [
    activeDraft?.persona_name,
    activeDraft?.response,
    lastHydratedDraft.personaName,
    lastHydratedDraft.response,
    polishedText,
  ]);

  useEffect(() => {
    if (drafts.length === 0) {
      return;
    }

    setInitialDraftResponses((current) => {
      const next = { ...current };
      let changed = false;

      for (const draft of drafts) {
        const candidateOriginal = (draft.raw_response || draft.response || "").trim();
        if (!candidateOriginal || next[draft.draft_id]) {
          continue;
        }
        next[draft.draft_id] = candidateOriginal;
        changed = true;
      }

      return changed ? next : current;
    });
  }, [drafts]);

  function getOriginalDraftResponse(draftId?: string | null) {
    /**
     * 输入：
     * - draftId：当前选中的草稿 ID；在批量场景下可能来自已持久化条目，在单条场景下来自工作台当前选项。
     * 输出：
     * - 返回该草稿首轮生成时的原始回复；若缓存里没有，再用现有条目或当前草稿正文兜底。
     * 作用：
     * - 保证“原始回复”字段始终指向首版 AI 草稿，而不是批注重生成后的新版本。
     */

    const persistedOriginal = activeBatchItem?.ai_selected_raw_response?.trim() ?? "";
    if (persistedOriginal) {
      return persistedOriginal;
    }

    if (draftId && initialDraftResponses[draftId]) {
      return initialDraftResponses[draftId];
    }

    return (activeDraft?.raw_response || activeDraft?.response || "").trim();
  }

  function getOriginalSafetyResponse(source?: string | null) {
    /**
     * 输入：
     * - source：当前安全回复候选来源标记，例如 `api`、`local` 或 `mock`。
     * 输出：
     * - 返回该来源候选最开始那版安全回复；如果缓存里没有，则退回当前候选正文。
     * 作用：
     * - 确保安全回复记录里的“原始回复”字段始终指向首版安全回复，而不是批注重生成后的版本。
     */

    if (source && initialSafetyResponsesBySource[source]) {
      return initialSafetyResponsesBySource[source];
    }

    return (activeSafetyCandidate?.safe_response || safetyState.result?.safe_response || "").trim();
  }

  function togglePersona(personaName: string) {
    setSelectedPersonas((current) => {
      if (current.includes(personaName)) {
        return current.filter((item) => item !== personaName);
      }
      return [...current, personaName];
    });
  }

  function goToBatchIndex(nextIndex: number) {
    if (nextIndex < 0 || nextIndex >= batchItems.length) {
      return;
    }
    setBatchCurrentIndex(nextIndex);
  }

  function handleSelectBatchRow(rowNumber: number) {
    const index = batchItems.findIndex((item) => item.row_number === rowNumber);
    if (index >= 0) {
      setWorkspaceMode("batch");
      goToBatchIndex(index);
    }
  }

  function handleAddSourceAnnotation(annotation: SourceAnnotation) {
    setSourceAnnotations((current) => [...current, annotation]);
  }

  function handleRemoveSourceAnnotation(annotationId: string) {
    setSourceAnnotations((current) => current.filter((item) => item.id !== annotationId));
  }

  function buildSampleSnapshot() {
    const normalizedExpertAnnotation = expertAnnotation.trim();
    const normalizedSampleReason = sampleReason.trim();
    const originalDraftResponse = getOriginalDraftResponse(activeDraft?.draft_id ?? selectedPersona);
    return {
      user_input: userInput,
      selected_persona_name:
        activeDraft?.persona_name ?? activeBatchItem?.selected_persona_name ?? selectedPersona ?? "",
      selected_persona_names: selectedPersonas,
      ai_selected_raw_response: originalDraftResponse,
      expert_polished_response: polishedText,
      expert_annotation: normalizedExpertAnnotation,
      sample_reason: normalizedSampleReason,
      evaluation: normalizeResponseEvaluation(responseEvaluation),
      source_annotations: sourceAnnotations,
      response_versions: responseVersions,
      active_version_index: activeVersionIndex,
    };
  }

  function deriveRagReady() {
    return expertAnnotation.trim() || sourceAnnotations.length > 0 ? "approved" : "pending";
  }

  async function handleGenerate() {
    setStatusText(null);
    setViewMode("workspace");
    setResponseEvaluation(EMPTY_EVALUATION);
    if (selectedPersonas.length === 0) {
      setStatusText("请先选择至少一种风格，再生成草稿。");
      return;
    }
    setInitialDraftResponses({});
    await startGeneration({
      user_input: userInput,
      persona_names: selectedPersonas,
      compare_sources: generationSourceMode === "compare",
      source_mode: generationSourceMode,
    });
  }

  async function handlePersistBatchItem(status: string, recordId?: number | null) {
    if (!activeBatchItem || !activeDraft) {
      return;
    }

    const originalDraftResponse = getOriginalDraftResponse(activeDraft.draft_id);
    const nextVersions =
      responseVersions.length > 0
        ? responseVersions
        : [
            {
              version_index: 0,
              label: "专家当前版本",
              response: polishedText,
              selected_persona_name: activeDraft.persona_name,
              created_at: new Date().toISOString(),
              source: "manual",
              source_annotations: sourceAnnotations,
            },
          ];

    const detail = await updateBatchSessionItem.mutateAsync({
      sessionId: activeBatchItem.session_id as number,
      itemId: activeBatchItem.id as number,
      payload: {
        selected_persona_names: selectedPersonas,
        selected_persona_name: activeDraft.persona_name,
        selected_style_config: activeDraft.style_config,
        planner_output: activeDraft.planner_output,
        draft_candidates: drafts,
        ai_selected_raw_response: originalDraftResponse,
        latest_response: polishedText,
        expert_annotation: expertAnnotation,
        rag_ready: deriveRagReady(),
        sample_reason: "",
        sample_tags: {},
        planner_labels: {},
        evaluation: normalizeResponseEvaluation(responseEvaluation),
        sample_snapshot: buildSampleSnapshot(),
        source_annotations: sourceAnnotations,
        response_versions: nextVersions,
        active_version_index: activeVersionIndex,
        status,
        record_id: recordId ?? activeBatchItem.record_id ?? null,
      },
    });

    if (detail.current_item_id) {
      const nextIndex = detail.items.findIndex((item) => item.id === detail.current_item_id);
      if (nextIndex >= 0) {
        setBatchCurrentIndex(nextIndex);
      }
    }
  }

  async function handleSave() {
    if (!activeDraft || !polishedText.trim()) {
      return;
    }

    const originalDraftResponse = getOriginalDraftResponse(activeDraft.draft_id);
    const nextVersions =
      responseVersions.length > 0
        ? responseVersions
        : [
            {
              version_index: 0,
              label: "专家当前版本",
              response: polishedText,
              selected_persona_name: activeDraft.persona_name,
              created_at: new Date().toISOString(),
              source: "manual",
              source_annotations: sourceAnnotations,
            },
          ];

    const payload = {
      user_input: userInput,
      selected_persona_name: activeDraft.persona_name,
      selected_style_config: activeDraft.style_config,
      planner_output: activeDraft.planner_output,
      draft_candidates: drafts,
      ai_selected_raw_response: originalDraftResponse,
      expert_polished_response: polishedText,
      expert_annotation: expertAnnotation,
      rag_ready: deriveRagReady(),
      sample_reason: "",
      sample_tags: {},
      planner_labels: {},
      evaluation: normalizeResponseEvaluation(responseEvaluation),
      sample_snapshot: buildSampleSnapshot(),
      source_annotations: sourceAnnotations,
      response_versions: nextVersions,
      batch_session_id: activeBatchItem?.session_id ?? null,
      batch_item_id: activeBatchItem?.id ?? null,
    };

    try {
      const record = await saveRecord.mutateAsync(payload);
      setStatusText(
        activeBatchItem
          ? `第 ${activeBatchItem.row_number} 行已保存并写入历史记录，已同步更新到持久批次。`
          : "这条记录已经保存到历史库。",
      );
      if (activeBatchItem) {
        await handlePersistBatchItem("completed", record.id);
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "保存失败");
    }
  }

  async function handleImportBatchExcel(file: File) {
    setStatusText(null);
    try {
      const result = await importBatchExcel.mutateAsync(file);
      setActiveSessionId(result.id);
      setWorkspaceMode("batch");
      setBatchFileName(file.name);
      setStatusText(`已创建并持久化批量任务，共 ${result.total_items} 条。关闭网页后仍可继续处理。`);
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "Excel 导入失败");
    }
  }

  async function handleExportReviewedBatch() {
    setStatusText(null);
    try {
      const blob = await exportReviewedBatch.mutateAsync(reviewedBatchItems);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "reviewed_batch_results.xlsx";
      anchor.click();
      window.URL.revokeObjectURL(url);
      setStatusText("已导出专家逐条完成后的最终结果 Excel。");
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "批量导出失败");
    }
  }

  async function handleRegenerateFromAnnotations() {
    if (!selectedPersona || sourceAnnotations.length === 0) {
      setStatusText("请先在 AI 回复中添加至少一条高亮批注，再进行重生成。");
      return;
    }

    try {
      if (!activeBatchItem) {
        const draftsFromRegenerate = await startGeneration({
          user_input: `${userInput}\n\n【当前 AI 回复】\n${polishedText}\n\n【专家对当前 AI 回复的高亮批注】\n${sourceAnnotations
            .map(
              (annotation, index) =>
                `${index + 1}. 回复片段：${annotation.quote || "未填写"}；专家批注：${annotation.note || "未填写"}`,
            )
            .join("\n")}\n\n【专家总体说明】\n${expertAnnotation}`.trim(),
          persona_names: selectedPersonas.length > 0 ? selectedPersonas : [activeDraft?.persona_name ?? "温暖倾听者"],
          compare_sources: generationSourceMode === "compare",
          source_mode: generationSourceMode,
        });

        const selectedDraft =
          draftsFromRegenerate.find((draft) => draft.draft_id === selectedPersona) ??
          draftsFromRegenerate[0] ??
          null;

        if (selectedDraft) {
          const originalDraftResponse = getOriginalDraftResponse(selectedPersona);
          const existingVersions =
            responseVersions.length > 0
              ? responseVersions
              : [
                  {
                    version_index: 0,
                    label: "专家当前版本",
                    response: polishedText,
                    selected_persona_name: activeDraft?.persona_name ?? "未标记风格",
                    created_at: new Date().toISOString(),
                    source: "manual",
                    source_annotations: sourceAnnotations,
                  },
                ];

          const nextVersion = {
            version_index: existingVersions.length,
            label: `批注重生成 v${existingVersions.length + 1}`,
            response: selectedDraft.response,
            selected_persona_name: selectedDraft.persona_name,
            created_at: new Date().toISOString(),
            source: "annotation_regenerate",
            source_annotations: sourceAnnotations,
          };

          setResponseVersions([...existingVersions, nextVersion]);
          setInitialDraftResponses((current) => {
            if (!selectedDraft.draft_id || current[selectedDraft.draft_id] || !originalDraftResponse) {
              return current;
            }
            return {
              ...current,
              [selectedDraft.draft_id]: originalDraftResponse,
            };
          });
          setActiveVersionIndex(nextVersion.version_index);
          setPolishedText(selectedDraft.response);
          setResponseEvaluation(EMPTY_EVALUATION);
          setSelectedPersona(selectedDraft.draft_id);
          setStatusText("已基于 AI 回复高亮批注重新生成，并新增一条可回退的回复版本。");
        }
        return;
      }

      const detail = await regenerateBatchSessionItem.mutateAsync({
        sessionId: activeBatchItem.session_id as number,
        itemId: activeBatchItem.id as number,
        payload: {
          selected_persona_name: activeDraft?.persona_name ?? activeBatchItem.selected_persona_name,
          selected_persona_names: selectedPersonas,
          source_annotations: sourceAnnotations,
          expert_annotation: expertAnnotation,
          current_response: polishedText,
          planner_output: activeDraft?.planner_output ?? activeBatchItem.planner_output_json ?? {},
        },
      });

      const updatedItem = detail.items.find((item) => item.id === activeBatchItem.id);
      if (updatedItem) {
        hydrateWorkspace({
          drafts: updatedItem.draft_candidates_json.map((draft) => ({
            draft_id: String(draft.draft_id ?? `${String(draft.persona_name ?? "")}::${String(draft.source ?? "api")}`),
            persona_name: String(draft.persona_name ?? ""),
            source: String(draft.source ?? "api"),
            source_label: String(draft.source_label ?? "API 模型"),
            style_config: (draft.style_config ?? {}) as Record<string, string>,
            planner_output: (draft.planner_output ?? {}) as Record<string, unknown>,
            response: String(draft.response ?? ""),
            raw_response: String(draft.raw_response ?? ""),
          })),
          selectedPersona: String(updatedItem.draft_candidates_json[0]?.draft_id ?? "") || selectedPersona,
        });
        setResponseVersions(updatedItem.response_versions_json ?? []);
        setActiveVersionIndex(updatedItem.active_version_index ?? 0);
        setPolishedText(updatedItem.latest_response ?? polishedText);
        setResponseEvaluation(EMPTY_EVALUATION);
        setStatusText("已基于 AI 回复高亮批注重新生成，并新增一条可回退的回复版本。");
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "批注重生成失败");
    }
  }

  function handlePlannerChange(plannerOutput: PlannerOutput) {
    if (!activeDraft) {
      return;
    }
    updateDraftPlanner(activeDraft.draft_id, plannerOutput);
    setStatusText("已应用 Planner 修改，可按修改后的 Planner 重生成全文。");
  }

  async function handleRegenerateFromPlanner(plannerOutput: PlannerOutput) {
    if (!activeDraft) {
      setStatusText("请先选择一份草稿。");
      return;
    }

    try {
      if (!currentBatchItem) {
        const selectedDraft = await generateDraftFromPlan({
          user_input: userInput,
          persona_name: activeDraft.persona_name,
          planner_output: plannerOutput,
          source_mode: generationSourceMode,
        });
        appendPlannerRegeneratedVersion(selectedDraft, plannerOutput);
        setStatusText("已按修改后的 Planner 重新生成全文，并新增一条可回退版本。");
        return;
      }

      const detail = await regenerateBatchSessionItem.mutateAsync({
        sessionId: currentBatchItem.session_id as number,
        itemId: currentBatchItem.id as number,
        payload: {
          selected_persona_name: activeDraft.persona_name,
          selected_persona_names: selectedPersonas.length > 0 ? selectedPersonas : [activeDraft.persona_name],
          source_annotations: sourceAnnotations,
          expert_annotation: expertAnnotation,
          current_response: polishedText,
          planner_output: plannerOutput,
        },
      });
      const updatedItem = detail.items.find((item) => item.id === currentBatchItem.id);
      if (updatedItem) {
        hydrateWorkspace({
          drafts: updatedItem.draft_candidates_json.map((draft) => ({
            draft_id: String(draft.draft_id ?? `${String(draft.persona_name ?? "")}::${String(draft.source ?? "api")}`),
            persona_name: String(draft.persona_name ?? ""),
            source: String(draft.source ?? "api"),
            source_label: String(draft.source_label ?? "API 模型"),
            style_config: (draft.style_config ?? {}) as Record<string, string>,
            planner_output: (draft.planner_output ?? {}) as Record<string, unknown>,
            response: String(draft.response ?? ""),
            raw_response: String(draft.raw_response ?? ""),
          })),
          selectedPersona: String(updatedItem.draft_candidates_json[0]?.draft_id ?? "") || selectedPersona,
        });
        setResponseVersions(updatedItem.response_versions_json ?? []);
        setActiveVersionIndex(updatedItem.active_version_index ?? 0);
        setPolishedText(updatedItem.latest_response ?? polishedText);
        setResponseEvaluation(EMPTY_EVALUATION);
        setStatusText("已按修改后的 Planner 重新生成全文，并新增一条可回退版本。");
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "按 Planner 重生成失败");
    }
  }

  function appendPlannerRegeneratedVersion(selectedDraft: DraftCandidate, plannerOutput: PlannerOutput) {
    const existingVersions =
      responseVersions.length > 0
        ? responseVersions
        : [
            {
              version_index: 0,
              label: "专家当前版本",
              response: polishedText,
              selected_persona_name: activeDraft?.persona_name ?? "未标记风格",
              created_at: new Date().toISOString(),
              source: "manual",
              source_annotations: sourceAnnotations,
            },
          ];

    const nextVersion = {
      version_index: existingVersions.length,
      label: `Planner 重生成 v${existingVersions.length + 1}`,
      response: selectedDraft.response,
      selected_persona_name: selectedDraft.persona_name,
      created_at: new Date().toISOString(),
      source: "planner_regenerate",
      source_annotations: sourceAnnotations,
    };

    updateDraftPlanner(selectedDraft.draft_id, selectedDraft.planner_output as PlannerOutput);
    setResponseVersions([...existingVersions, nextVersion]);
    setActiveVersionIndex(nextVersion.version_index);
    setPolishedText(selectedDraft.response);
    setResponseEvaluation(EMPTY_EVALUATION);
    setSelectedPersona(selectedDraft.draft_id);
  }

  async function handleRollbackVersion(versionIndex: number) {
    if (!activeBatchItem) {
      const version = responseVersions.find((item) => item.version_index === versionIndex);
      if (!version) {
        return;
      }
      setActiveVersionIndex(versionIndex);
      setPolishedText(version.response);
      setSelectedPersona(version.selected_persona_name);
      setSourceAnnotations(version.source_annotations ?? []);
      setResponseEvaluation(EMPTY_EVALUATION);
      setStatusText(`已回退到版本 ${versionIndex + 1}。`);
      return;
    }
    try {
      const detail = await rollbackBatchSessionItem.mutateAsync({
        sessionId: activeBatchItem.session_id as number,
        itemId: activeBatchItem.id as number,
        versionIndex,
      });
      const updatedItem = detail.items.find((item) => item.id === activeBatchItem.id);
      if (updatedItem) {
        setResponseVersions(updatedItem.response_versions_json ?? []);
        setActiveVersionIndex(updatedItem.active_version_index ?? 0);
        setPolishedText(updatedItem.latest_response ?? polishedText);
        setSelectedPersonas(updatedItem.selected_persona_names_json ?? selectedPersonas);
        setSourceAnnotations(updatedItem.source_annotations_json ?? sourceAnnotations);
        setResponseEvaluation(EMPTY_EVALUATION);
        setStatusText(`已回退到版本 ${versionIndex + 1}。`);
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "版本回退失败");
    }
  }

  async function handleSafetyCheck() {
    if (isWorkspaceBatchMode) {
      return;
    }

    setSafetyStatusText(null);
    setSafetySaveStatusText(null);
    setSafetyRegenerateStatusText(null);
    try {
      const result = await runSafetyCheck({
        user_input: userInput,
        source_mode: generationSourceMode,
      });
      if (result.is_safe) {
        setCorrectedRiskLabels(result.risk_labels);
        setSelectedSafetyResponseSource(null);
        setSafetySourceUserInput("");
        setSafetyPolishedText("");
        setInitialSafetyResponsesBySource({});
        setSafetySourceAnnotations([]);
        setSafetyExpertAnnotation("");
        setIsSafetyPolishVisible(false);
        setViewMode("workspace");
        setSafetyStatusText("检测结果为安全，中间区域保持常规工作台布局。");
        return;
      }

      const nextSafetyCandidate = getActiveSafetyResponseCandidate(result, null);
      setCorrectedRiskLabels(result.risk_labels);
      setSelectedSafetyResponseSource(nextSafetyCandidate?.source ?? null);
      setSafetySourceUserInput(userInput);
      setSafetyPolishedText(nextSafetyCandidate?.safe_response ?? result.safe_response ?? "");
      setInitialSafetyResponsesBySource(buildInitialSafetyResponseMap(result));
      setSafetySourceAnnotations([]);
      setSafetyExpertAnnotation("");
      setIsSafetyPolishVisible(false);
      setSafetyStatusText("检测到需要优先处理的风险信号，中间区域已切换为安全回复结果页。");
      setViewMode("safety");
    } catch {
      // Error state is already stored in the hook.
    }
  }

  function handleBackToWorkspace() {
    if (hasUnsafeSafetyResult) {
      setSafetyStatusText("已返回常规工作台，你仍然可以在中间区域重新查看上次安全回复。");
    }
    setViewMode("workspace");
  }

  function handleReopenSafetyResult() {
    if (!hasUnsafeSafetyResult) {
      return;
    }
    setSafetyStatusText("已重新打开上次安全回复结果页。");
    setViewMode("safety");
  }

  function handleToggleSafetyPolish() {
    setIsSafetyPolishVisible((current) => {
      const nextVisible = !current;
      const currentSafetyCandidate = getActiveSafetyResponseCandidate(
        safetyState.status === "success" ? safetyState.result : null,
        selectedSafetyResponseSource,
      );

      if (
        nextVisible &&
        !safetyPolishedText.trim() &&
        safetyState.status === "success" &&
        (currentSafetyCandidate?.safe_response || safetyState.result?.safe_response)
      ) {
        setSafetyPolishedText(
          currentSafetyCandidate?.safe_response || safetyState.result.safe_response || "",
        );
      }

      return nextVisible;
    });
  }

  function handleSafetyResponseSourceChange(source: string) {
    /**
     * 输入：
     * - source：用户在安全回复对比模式下新选中的候选来源。
     * 输出：
     * - 切换页面当前展示和润色的安全回复正文，并清空上一候选对应的批注状态。
     * 作用：
     * - 避免不同来源候选之间误复用同一组高亮位置和专家说明，导致批注落在错误的回复文本上。
     */

    const nextCandidate = getActiveSafetyResponseCandidate(
      safetyState.status === "success" ? safetyState.result : null,
      source,
    );
    setSelectedSafetyResponseSource(source);

    if (nextCandidate?.safe_response) {
      setSafetyPolishedText(nextCandidate.safe_response);
    }
    setSafetySourceAnnotations([]);
    setSafetyExpertAnnotation("");
    setSafetyRegenerateStatusText(null);
  }

  function handleAddSafetySourceAnnotation(annotation: SourceAnnotation) {
    /**
     * 输入：
     * - annotation：用户在安全回复润色区新添加的一条高亮批注。
     * 输出：
     * - 将该批注追加到当前安全回复批注列表。
     * 作用：
     * - 让安全回复页复用普通对话的划词批注能力，为后续“按批注重生成”准备结构化输入。
     */

    setSafetySourceAnnotations((current) => [...current, annotation]);
  }

  function handleRemoveSafetySourceAnnotation(annotationId: string) {
    /**
     * 输入：
     * - annotationId：要删除的安全回复高亮批注 ID。
     * 输出：
     * - 从当前安全回复批注列表中移除对应项。
     * 作用：
     * - 允许专家在正式重生成前及时清理误选或过期批注，减少错误意图进入生成链路的概率。
     */

    setSafetySourceAnnotations((current) => current.filter((item) => item.id !== annotationId));
  }

  async function handleRegenerateSafetyReply() {
    /**
     * 输入：
     * - 当前安全检测结果、选中的安全回复来源、专家高亮批注与总体说明。
     * 输出：
     * - 调用安全回复重生成接口，并把新的候选结果回写到当前安全结果与润色区。
     * 作用：
     * - 让安全回复页也能像普通对话一样，围绕当前回复和专家意图快速迭代出更贴近需求的新版本。
     */

    if (safetyState.status !== "success" || !safetyState.result || safetyState.result.is_safe) {
      return;
    }

    if (!activeSafetyCandidate) {
      setSafetyRegenerateStatusText("当前没有可重生成的安全回复候选。");
      return;
    }

    if (safetySourceAnnotations.length === 0) {
      setSafetyRegenerateStatusText("请先在安全回复中添加至少一条高亮批注，再进行重生成。");
      return;
    }

    const payload: SafetyRegenerateRequest = {
      user_input: safetySourceUserInput || userInput,
      risk_codes: safetyState.result.risk_codes,
      corrected_risk_labels: correctedRiskLabels,
      risk_reason: safetyState.result.reason,
      source: activeSafetyCandidate.source as "api" | "local" | "mock",
      current_response: safetyPolishedText || activeSafetyCandidate.safe_response,
      source_annotations: safetySourceAnnotations,
      expert_annotation: safetyExpertAnnotation,
    };

    try {
      const nextCandidate = await regenerateSafetyReply.mutateAsync(payload);
      const existingCandidates = safetyState.result.safe_response_candidates ?? [];
      const nextCandidates =
        existingCandidates.length > 0
          ? existingCandidates.map((candidate) =>
              candidate.source === nextCandidate.source ? nextCandidate : candidate,
            )
          : [nextCandidate];
      const nextResult: SafetyCheckResponse = {
        ...safetyState.result,
        intent: nextCandidate.intent ?? safetyState.result.intent,
        safe_response: nextCandidate.safe_response,
        safe_highlight_segments: nextCandidate.safe_highlight_segments ?? [],
        safe_highlight_source: nextCandidate.safe_highlight_source ?? null,
        safe_response_candidates: nextCandidates,
      };

      replaceSafetyResult(nextResult);
      setInitialSafetyResponsesBySource((current) => {
        if (current[nextCandidate.source]) {
          return current;
        }
        return {
          ...current,
          [nextCandidate.source]:
            (activeSafetyCandidate.safe_response || safetyState.result?.safe_response || "").trim(),
        };
      });
      setSelectedSafetyResponseSource(nextCandidate.source);
      setSafetyPolishedText(nextCandidate.safe_response);
      setSafetySourceAnnotations([]);
      setSafetyExpertAnnotation("");
      setIsSafetyPolishVisible(true);
      setSafetyRegenerateStatusText("已基于安全回复批注生成新版本，请继续润色或重新高亮。");
    } catch (error) {
      setSafetyRegenerateStatusText(
        error instanceof Error ? error.message : "安全回复重生成失败",
      );
    }
  }

  async function handleSaveSafetyRecord() {
    if (safetyState.status !== "success" || !safetyState.result || safetyState.result.is_safe) {
      return;
    }

    try {
      await saveSafetyRecord.mutateAsync({
        user_input: safetySourceUserInput || userInput,
        risk_labels: safetyState.result.risk_labels,
        corrected_risk_labels: correctedRiskLabels,
        risk_reason: safetyState.result.reason,
        ai_safe_response: getOriginalSafetyResponse(activeSafetyCandidate?.source),
        expert_polished_response: safetyPolishedText,
      });
      setSafetySaveStatusText("这条安全回复记录已经保存到安全样本库。");
    } catch (error) {
      setSafetySaveStatusText(error instanceof Error ? error.message : "安全回复记录保存失败");
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-8 xl:px-10">
      <div className="mx-auto max-w-[1760px]">
        <header className="mb-6 overflow-hidden rounded-panel border border-line bg-white/80 p-6 shadow-soft backdrop-blur">
          <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <div className="inline-flex items-center rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.22em] text-amber">
                Mindful Copilot Workspace
              </div>
              <h1 className="mt-4 font-serif text-4xl text-ink md:text-5xl">心灵笔友</h1>
              <p className="mt-4 max-w-4xl text-sm leading-8 text-ink/72">
                一个面向心理疏导专家的 AI 协同工作台。
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-3 xl:min-w-[640px]">
              <div className="rounded-[26px] border border-line bg-paper/72 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-ink/42">当前模式</p>
                <p className="mt-2 text-lg font-semibold text-ink">{isBatchMode ? "持久批量处理" : "单条工作模式"}</p>
              </div>
              <div className="rounded-[26px] border border-line bg-paper/72 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-ink/42">已选风格</p>
                <p className="mt-2 text-lg font-semibold text-ink">{selectedPersonas.length} 个</p>
              </div>
              <div className="rounded-[26px] border border-line bg-paper/72 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-ink/42">批量进度</p>
                <p className="mt-2 text-lg font-semibold text-ink">
                  {isWorkspaceBatchMode && isBatchMode ? `${batchCompletedCount} / ${batchItems.length}` : "未启用"}
                </p>
              </div>
            </div>
          </div>
          <div className="mt-6 flex flex-col gap-3 border-t border-line/80 pt-6 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-3">
              <div className="inline-flex rounded-full border border-line bg-white/72 p-1">
                <button
                  type="button"
                  onClick={() => setWorkspaceMode("single")}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    !isWorkspaceBatchMode ? "bg-amber text-white" : "text-ink/72"
                  }`}
                >
                  普通模式
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setWorkspaceMode("batch");
                    setViewMode("workspace");
                  }}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    isWorkspaceBatchMode ? "bg-amber text-white" : "text-ink/72"
                  }`}
                >
                  批量模式
                </button>
              </div>
              <div className="inline-flex rounded-full border border-line bg-white/72 p-1">
                {[
                  { value: "auto", label: "自动" },
                  { value: "api", label: "API" },
                  { value: "vllm", label: "vLLM" },
                  { value: "compare", label: "对比" },
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() =>
                      setGenerationSourceMode(option.value as "auto" | "api" | "vllm" | "compare")
                    }
                    className={`rounded-full px-4 py-2 text-sm transition ${
                      generationSourceMode === option.value ? "bg-amber text-white" : "text-ink/72"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={jobLoading || selectedPersonas.length === 0 || !userInput.trim()}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-amber px-6 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45"
              >
                <Sparkles size={16} />
                {jobLoading ? "生成中..." : "生成多种草稿"}
              </button>
              <button
                type="button"
                onClick={() => setRightPanelMode("evaluation")}
                disabled={!activeDraft && !polishedText.trim()}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/70 px-5 py-3 text-sm text-ink transition hover:bg-paper/85 disabled:cursor-not-allowed disabled:opacity-45"
              >
                评价当前回复
              </button>
              <button
                type="button"
                onClick={handleRegenerateFromAnnotations}
                disabled={!activeBatchItem || regenerateBatchSessionItem.isPending}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/70 px-5 py-3 text-sm text-ink transition hover:bg-paper/85 disabled:cursor-not-allowed disabled:opacity-45"
              >
                <RefreshCcw size={16} />
                {regenerateBatchSessionItem.isPending ? "重生成中..." : "按批注重生成"}
              </button>
              <Link
                to="/records"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/70 px-5 py-3 text-sm text-ink transition hover:bg-paper/85"
              >
                <ScrollText size={16} />
                查看历史记录
              </Link>
            </div>
            <div className="rounded-full bg-white/72 px-4 py-2 text-sm text-ink/72">
              {isWorkspaceBatchMode && isBatchMode
                ? "支持刷新后恢复批次、原文高亮批注、基于批注重生成和版本回退"
                : generationSourceMode === "compare"
                  ? "当前会同时对比 API 与本地 vLLM 回复"
                  : generationSourceMode === "api"
                    ? "当前只生成 API 模型回复"
                    : generationSourceMode === "vllm"
                      ? "当前只生成本地 vLLM 回复"
                      : "建议一次比较 2 至 3 种风格"}
            </div>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[440px_minmax(0,1fr)_360px] 2xl:grid-cols-[480px_minmax(0,1fr)_380px]">
          <div className="grid gap-6">
            <UserLetterPanel
              value={userInput}
              onChange={setUserInput}
              readOnly={Boolean(activeBatchItem)}
              headerAside={
                !isWorkspaceBatchMode ? (
                  <SafetyCheckBar
                    canCheck={Boolean(userInput.trim())}
                    isChecking={isChecking}
                    onCheck={handleSafetyCheck}
                    statusText={safetyStatusText}
                    errorText={safetyState.status === "error" ? safetyState.error : null}
                    variant="inline"
                  />
                ) : null
              }
              batchMeta={
                activeBatchItem
                  ? {
                      current: batchCurrentIndex + 1,
                      total: batchItems.length,
                      rowNumber: activeBatchItem.row_number,
                    }
                  : null
              }
            />
          </div>

          <div className="grid gap-6">
            {!isWorkspaceBatchMode && viewMode === "safety" && safetyState.status === "success" && safetyState.result ? (
              <SafetyResultPanel
                result={safetyState.result}
                selectedRiskLabels={correctedRiskLabels}
                onRiskLabelsChange={setCorrectedRiskLabels}
                selectedSafetyResponseSource={selectedSafetyResponseSource}
                onSafetyResponseSourceChange={handleSafetyResponseSourceChange}
                safetyPolishedText={safetyPolishedText}
                onSafetyPolishedTextChange={setSafetyPolishedText}
                safetySourceAnnotations={safetySourceAnnotations}
                onAddSafetySourceAnnotation={handleAddSafetySourceAnnotation}
                onRemoveSafetySourceAnnotation={handleRemoveSafetySourceAnnotation}
                safetyExpertAnnotation={safetyExpertAnnotation}
                onSafetyExpertAnnotationChange={setSafetyExpertAnnotation}
                isSafetyPolishVisible={isSafetyPolishVisible}
                onToggleSafetyPolish={handleToggleSafetyPolish}
                canRegenerateSafetyReply={Boolean(safetySourceAnnotations.length > 0)}
                isRegeneratingSafetyReply={regenerateSafetyReply.isPending}
                onRegenerateSafetyReply={handleRegenerateSafetyReply}
                safetyRegenerateStatusText={safetyRegenerateStatusText}
                canSaveSafetyRecord={Boolean(safetyPolishedText.trim() && correctedRiskLabels.length > 0)}
                isSavingSafetyRecord={saveSafetyRecord.isPending}
                onSaveSafetyRecord={handleSaveSafetyRecord}
                safetySaveStatusText={safetySaveStatusText}
                onBack={handleBackToWorkspace}
              />
            ) : (
              <>
                {!isWorkspaceBatchMode && hasUnsafeSafetyResult ? (
                  <section className="rounded-panel border border-line bg-white/74 p-6 shadow-soft">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-sm uppercase tracking-[0.22em] text-moss">安全回复暂存</p>
                        <p className="mt-2 text-sm leading-6 text-ink/68">
                          你已经返回常规工作台，如果需要继续参考刚才的安全回复，可以从这里回到结果页。
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={handleReopenSafetyResult}
                        className="rounded-full border border-line bg-paper/70 px-5 py-3 text-sm text-ink transition hover:bg-white"
                      >
                        查看上次安全回复
                      </button>
                    </div>
                  </section>
                ) : null}

                {isLoading ? (
                  <LoadingSkeleton />
                ) : (
                  <PersonaSelector
                    personas={personas}
                    selected={selectedPersonas}
                    onToggle={togglePersona}
                  />
                )}

                {jobError ? <p className="text-sm text-red-600">{jobError}</p> : null}
                {statusText ? (
                  <div className="rounded-[24px] border border-line bg-white/72 px-5 py-4 text-sm leading-7 text-moss shadow-card">
                    {statusText}
                  </div>
                ) : null}

                <DraftStreamTabs drafts={drafts} selectedPersona={selectedPersona} onSelect={setSelectedPersona} />

                <PlannerInsightAccordion
                  plannerOutput={activeDraft?.planner_output}
                  onChange={handlePlannerChange}
                  onRegenerate={handleRegenerateFromPlanner}
                  regenerating={jobLoading || regenerateBatchSessionItem.isPending}
                />

                <section className="grid gap-5 rounded-panel border border-line bg-white/76 p-6 shadow-soft">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                      <p className="text-sm uppercase tracking-[0.22em] text-moss">Step 3 & 4</p>
                      <h2 className="mt-2 font-serif text-3xl text-ink">
                        {activeDraft?.persona_name ?? activeBatchItem?.selected_persona_name ?? "先选择一份草稿"}
                      </h2>
                      <p className="mt-2 text-sm leading-7 text-ink/66">
                        先对选中的草稿做最终润色，再记录本次人工判断与修改原因，方便后续复盘和高质量数据沉淀。
                      </p>
                    </div>
                    <div className="rounded-[24px] border border-line bg-paper/75 px-4 py-3 text-sm text-ink/72">
                      当前工作流：生成草稿 → 润色回复并高亮批注 → 基于批注重生成 → 保存
                    </div>
                  </div>
                  <ToneGuideBar styleConfig={activeDraft?.style_config ?? activeBatchItem?.selected_style_config_json} />
                  <PolishingEditor
                    value={polishedText}
                    onChange={setPolishedText}
                    annotations={sourceAnnotations}
                    onAddAnnotation={handleAddSourceAnnotation}
                    onRemoveAnnotation={handleRemoveSourceAnnotation}
                  />
                  <ExpertAnnotationPanel
                    value={expertAnnotation}
                    onChange={setExpertAnnotation}
                    sampleReason={sampleReason}
                    onSampleReasonChange={setSampleReason}
                  />
                  <ResponseVersionPanel
                    versions={responseVersions}
                    activeVersionIndex={activeVersionIndex}
                    canRegenerate={Boolean(selectedPersona && sourceAnnotations.length > 0)}
                    regenerating={regenerateBatchSessionItem.isPending || jobLoading}
                    onRegenerate={handleRegenerateFromAnnotations}
                    onRollback={handleRollbackVersion}
                  />
                  <SaveRecordBar
                    canSave={Boolean(activeDraft && polishedText.trim())}
                    isSaving={saveRecord.isPending || updateBatchSessionItem.isPending}
                    onSave={handleSave}
                    batchMode={Boolean(activeBatchItem)}
                    allCompleted={batchAllCompleted}
                    onExportReviewedBatch={activeBatchItem ? handleExportReviewedBatch : null}
                    exportingReviewedBatch={exportReviewedBatch.isPending}
                  />
                </section>
              </>
            )}
          </div>

          <div className="grid gap-4 xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)] xl:self-start xl:overflow-y-auto xl:pr-1">
            {isWorkspaceBatchMode ? (
              <div className="inline-flex rounded-full border border-line bg-white/72 p-1">
                <button
                  type="button"
                  onClick={() => setRightPanelMode("batch")}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    rightPanelMode === "batch" ? "bg-amber text-white" : "text-ink/72"
                  }`}
                >
                  批量任务
                </button>
                <button
                  type="button"
                  onClick={() => setRightPanelMode("evaluation")}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    rightPanelMode === "evaluation" ? "bg-amber text-white" : "text-ink/72"
                  }`}
                >
                  评价模块
                </button>
              </div>
            ) : null}

            {rightPanelMode === "evaluation" || !isWorkspaceBatchMode ? (
              <ResponseEvaluationPanel
                value={responseEvaluation}
                onChange={setResponseEvaluation}
                defaultOpen
              />
            ) : null}

            {isWorkspaceBatchMode && rightPanelMode === "batch" ? (
              <BatchExcelPanel
                importing={importBatchExcel.isPending || batchSessions.isLoading}
                fileName={batchFileName}
                items={batchItems}
                completedCount={batchCompletedCount}
                currentIndex={batchCurrentIndex}
                activeRowNumber={currentBatchItem?.row_number ?? null}
                completedRowNumbers={completedRowNumbers}
                onImport={handleImportBatchExcel}
                onSelectRow={handleSelectBatchRow}
                onPrevious={() => goToBatchIndex(batchCurrentIndex - 1)}
                onNext={() => goToBatchIndex(batchCurrentIndex + 1)}
              />
            ) : null}
          </div>
        </div>

      </div>
    </main>
  );
}
