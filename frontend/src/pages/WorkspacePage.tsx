import { Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { LogOut, ScrollText, Sparkles } from "lucide-react";

import { useAuth } from "../app/auth";
import { BatchExcelPanel } from "../components/BatchExcelPanel";
import { DraftStreamTabs } from "../components/DraftStreamTabs";
import { MailThreadContextPanel } from "../components/MailThreadContextPanel";
import { PlannerInsightAccordion } from "../components/PlannerInsightAccordion";
import { PolishingEditor } from "../components/PolishingEditor";
import {
  EMPTY_EVALUATION,
  normalizeResponseEvaluation,
  ResponseEvaluationPanel,
} from "../components/ResponseEvaluationPanel";
import { ResponseVersionPanel } from "../components/ResponseVersionPanel";
import { SaveRecordBar } from "../components/SaveRecordBar";
import { UserLetterPanel } from "../components/UserLetterPanel";
import scirScLogo from "../assets/logo-mark.png";
import { useGenerationWorkspace, usePersonas } from "../features/generation/hooks";
import type { DraftCandidate, PlannerOutput } from "../features/generation/types";
import {
  useCreateAssignedThreadsWorkspaceSession,
} from "../features/mailThreads/hooks";
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
import type {
  BatchSessionItem,
  ResponseVersion,
  ResponseEvaluation,
  ReviewedBatchItem,
  SourceAnnotation,
  MailThreadWorkspaceContext,
} from "../features/records/types";

type WorkspaceMode = "single" | "excel_batch" | "mail_batch";
type WorkspaceBatchItem = ReturnType<typeof mapBatchSessionItem>;
const DEFAULT_PERSONA_NAME = "理性破局教练";
const PERSONA_DISPLAY_NAMES: Record<string, string> = {
  "标准书信回复": "标准书信回复",
  "理性破局教练": "理性分析助手",
};

function getPersonaDisplayName(personaName: string) {
  return PERSONA_DISPLAY_NAMES[personaName] ?? personaName;
}

const DEFAULT_INPUT = `这段时间我过得特别难受。每天早上想到要去学校，心里就沉甸甸的，很害怕。我不是不想学习，但上课时总控制不住地分心，总担心同学在背后议论我。放学我也尽量绕路，躲开那几个经常堵我的同学。

这些事压得我快喘不过气了。我试过想跟爸妈或者别人说，但话到嘴边又说不出来，怕没人信，也怕情况变得更糟。现在晚上经常失眠，躲在被子里哭，白天还要强撑着，感觉特别累，好像下一秒就要垮掉。

我真的不知道该怎么办了，感觉自己快扛不住了。您能给我一点建议吗？`;

function buildReviewedItems(items: WorkspaceBatchItem[]): ReviewedBatchItem[] {
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

function mapBatchSessionItem(item: BatchSessionItem) {
  return {
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
    risk_assessment_json: item.risk_assessment_json,
    source_annotations_json: item.source_annotations_json,
    response_versions_json: item.response_versions_json,
    active_version_index: item.active_version_index,
    status: item.status,
    record_id: item.record_id,
    mail_thread_id: item.mail_thread_id,
    context_json: item.context_json,
  };
}

function isMailThreadContext(value: unknown): value is MailThreadWorkspaceContext {
  return Boolean(value && typeof value === "object" && (value as MailThreadWorkspaceContext).kind === "mail_thread_reply");
}

function buildGenerationInput(userInput: string, context: unknown) {
  if (!isMailThreadContext(context)) {
    return userInput;
  }
  const transcript = (context.transcript ?? [])
    .map((message) => `${message.label || "书信"}：\n${message.content || ""}`)
    .join("\n\n");
  const risk = context.risk;
  const riskBlock =
    risk && risk.level && risk.level !== "NONE"
      ? `【风险提示】\n等级：${risk.level}\n触发因素：${risk.signals?.join("；") || risk.reasoning || "无"}\n\n`
      : "";
  const memorySummary = (context.memory_summary || "")
    .split("\n")
    .filter((line) => !line.trim().startsWith("风险趋势："))
    .join("\n")
    .trim();
  const memory = memorySummary ? `【系统记忆摘要】\n${memorySummary}\n\n` : "";
  return [
    "【当前用户来信】",
    userInput,
    "",
    memory.trim(),
    riskBlock.trim(),
    "【统一回应策略】理性分析",
    `【用户署名】${context.signature || "匿名"}`,
    "",
    transcript ? `【完整书信往返】\n${transcript}` : "",
    "",
    context.instruction ||
      "请为咨询师生成一封可审阅修改后发送给用户的书信式回信。需要参考完整上下文和风险提示；不要声称自己是 AI；不要替代医疗诊断或治疗。",
  ]
    .filter((part) => part.trim())
    .join("\n\n");
}

function splitLegacyMailThreadInput(value: string) {
  if (!value.includes("【完整书信往返】") || !value.includes("请为咨询师生成")) {
    return { userInput: value, context: null as MailThreadWorkspaceContext | null };
  }
  const userMatch = value.match(/用户来信：\n([\s\S]*?)(?:\n\n请为咨询师生成|\n\n既往回信：|$)/);
  const memoryMatch = value.match(/【系统记忆摘要】\n([\s\S]*?)\n\n【风险提示】/);
  const riskMatch =
    value.match(/【风险提示】\n等级：([^\n]+)\n触发因素：([\s\S]*?)\n\n【统一回应策略】/) ??
    value.match(/【风险提示】\n等级：([^\n]+)\n触发因素：([\s\S]*?)\n\n【用户回应偏好】/);
  const preferenceMatch = value.match(/【用户回应偏好】([^\n]+)/);
  const signatureMatch = value.match(/【用户署名】([^\n]+)/);
  const transcriptMatch = value.match(/【完整书信往返】\n([\s\S]*?)\n\n请为咨询师生成/);
  const userLetter = userMatch?.[1]?.trim() || value;
  const transcriptText = transcriptMatch?.[1]?.trim() || "";
  return {
    userInput: userLetter,
    context: {
      kind: "mail_thread_reply",
      signature: signatureMatch?.[1]?.trim() || "匿名",
      response_preference: preferenceMatch?.[1]?.trim() || "理性分析",
      memory_summary: memoryMatch?.[1]?.trim() || "",
      risk: {
        level: riskMatch?.[1]?.trim() || "NONE",
        signals: riskMatch?.[2]?.trim() ? [riskMatch[2].trim()] : [],
      },
      transcript: transcriptText
        ? [
            {
              label: "用户来信",
              content: userLetter,
            },
          ]
        : [],
      instruction:
        "请为咨询师生成一封可审阅修改后发送给用户的书信式回信。需要参考完整上下文和风险提示；不要声称自己是 AI；不要替代医疗诊断或治疗。",
    },
  };
}

function isMailBatchItem(item: Pick<WorkspaceBatchItem, "mail_thread_id" | "context_json">) {
  return Boolean(item.mail_thread_id || isMailThreadContext(item.context_json));
}

export function WorkspacePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { data } = usePersonas();
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
  const importBatchExcel = useImportBatchExcel();
  const updateBatchSessionItem = useUpdateBatchSessionItem();
  const regenerateBatchSessionItem = useRegenerateBatchSessionItem();
  const rollbackBatchSessionItem = useRollbackBatchSessionItem();
  const exportReviewedBatch = useExportReviewedBatch();
  const createAssignedThreadsWorkspace = useCreateAssignedThreadsWorkspaceSession();

  const personas = useMemo(() => {
    const catalog = data?.personas ?? [];
    const defaultPersona = catalog.find((persona) => persona.name === DEFAULT_PERSONA_NAME);
    return defaultPersona ? [defaultPersona] : catalog.slice(0, 1);
  }, [data?.personas]);
  const availableSessions = batchSessions.data?.items ?? [];

  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const batchSession = useBatchSession(activeSessionId);
  const sessionDetail = batchSession.data;

  const batchItems = useMemo(
    () => (sessionDetail?.items ?? []).map(mapBatchSessionItem),
    [sessionDetail?.items],
  );

  const [userInput, setUserInput] = useState(DEFAULT_INPUT);
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>([]);
  const [polishedText, setPolishedText] = useState("");
  const [expertAnnotation, setExpertAnnotation] = useState("");
  const [statusText, setStatusText] = useState<string | null>(null);
  const [batchFileName, setBatchFileName] = useState<string | null>(null);
  const [batchCurrentIndex, setBatchCurrentIndex] = useState(0);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("single");
  const [sourceAnnotations, setSourceAnnotations] = useState<SourceAnnotation[]>([]);
  const [responseVersions, setResponseVersions] = useState<ResponseVersion[]>([]);
  const [responseEvaluation, setResponseEvaluation] = useState<ResponseEvaluation>(EMPTY_EVALUATION);
  const [activeVersionIndex, setActiveVersionIndex] = useState(0);
  const [lastHydratedDraft, setLastHydratedDraft] = useState<{
    personaName: string | null;
    response: string;
  }>({
    personaName: null,
    response: "",
  });
  const routeState = location.state as { batchSessionId?: number; workspaceMode?: WorkspaceMode | "batch"; statusText?: string } | null;

  const isBatchMode = batchItems.length > 0;
  const isWorkspaceBatchMode = workspaceMode !== "single";
  const isMailBatchMode = workspaceMode === "mail_batch";
  const sessionLooksLikeMailBatch = batchItems.some(isMailBatchItem);
  const sessionMatchesMode = isWorkspaceBatchMode && (isMailBatchMode ? sessionLooksLikeMailBatch : !sessionLooksLikeMailBatch);
  const visibleBatchItems = sessionMatchesMode ? batchItems : [];
  const currentBatchItem = sessionMatchesMode && isBatchMode ? batchItems[batchCurrentIndex] ?? null : null;
  const hasVisibleBatch = visibleBatchItems.length > 0;
  const batchCompletedCount = visibleBatchItems.filter((item) => item.status === "completed").length;
  const batchAllCompleted = visibleBatchItems.length > 0 && batchCompletedCount === visibleBatchItems.length;
  const completedRowNumbers = visibleBatchItems.filter((item) => item.status === "completed").map((item) => item.row_number);
  const reviewedBatchItems = buildReviewedItems(visibleBatchItems);
  const legacySplit = currentBatchItem ? splitLegacyMailThreadInput(currentBatchItem.user_input) : null;
  const currentWorkspaceContext =
    currentBatchItem && isMailThreadContext(currentBatchItem.context_json)
      ? currentBatchItem.context_json
      : legacySplit?.context ?? null;
  useEffect(() => {
    if (routeState?.batchSessionId) {
      setActiveSessionId(routeState.batchSessionId);
      const nextMode = routeState.workspaceMode === "batch" ? "mail_batch" : routeState.workspaceMode ?? "excel_batch";
      setWorkspaceMode(nextMode);
      if (routeState.statusText) {
        setStatusText(routeState.statusText);
      }
      navigate(".", { replace: true, state: null });
      return;
    }
    if (activeSessionId !== null) {
      return;
    }
    const inProgress = availableSessions.find((session) => session.status !== "completed");
    const fallback = availableSessions[0] ?? null;
    const nextSession = inProgress ?? fallback;
    if (nextSession) {
      setActiveSessionId(nextSession.id);
    }
  }, [activeSessionId, availableSessions, navigate, routeState?.batchSessionId, routeState?.statusText, routeState?.workspaceMode]);

  useEffect(() => {
    if (!isBatchMode && personas.length > 0 && selectedPersonas.length === 0) {
      setSelectedPersonas([personas[0].name]);
    }
  }, [isBatchMode, personas, selectedPersonas.length]);

  useEffect(() => {
    if (!personas[0]?.name) {
      return;
    }
    if (selectedPersonas.length !== 1 || selectedPersonas[0] !== personas[0].name) {
      setSelectedPersonas([personas[0].name]);
    }
  }, [personas, selectedPersonas]);

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
    if (!currentBatchItem) {
      return;
    }

    resetWorkspace();
    const splitInput = splitLegacyMailThreadInput(currentBatchItem.user_input);
    setUserInput(splitInput.userInput);
    setSelectedPersonas(personas[0]?.name ? [personas[0].name] : currentBatchItem.selected_persona_names ?? []);
    setSourceAnnotations(currentBatchItem.source_annotations_json ?? []);
    setResponseVersions(currentBatchItem.response_versions_json ?? []);
    setActiveVersionIndex(currentBatchItem.active_version_index ?? 0);
    setExpertAnnotation(currentBatchItem.expert_annotation ?? "");
    setResponseEvaluation(
      normalizeResponseEvaluation((currentBatchItem.evaluation_json as ResponseEvaluation) ?? EMPTY_EVALUATION),
    );
    setPolishedText(currentBatchItem.latest_response ?? "");
    setStatusText(
      currentBatchItem.status === "completed"
        ? `已恢复第 ${batchCurrentIndex + 1} / ${visibleBatchItems.length} 条，当前为已完成状态，可回看版本或继续修改。`
        : `已恢复第 ${batchCurrentIndex + 1} / ${visibleBatchItems.length} 条，请继续处理。`,
    );

    if (currentBatchItem.draft_candidates_json?.length) {
      hydrateWorkspace({
        drafts: currentBatchItem.draft_candidates_json.map((draft) => ({
          draft_id: String(draft.draft_id ?? `${String(draft.persona_name ?? "")}::${String(draft.source ?? "api")}`),
          persona_name: String(draft.persona_name ?? ""),
          source: String(draft.source ?? "api"),
          source_label: String(draft.source_label ?? "API 模型"),
          style_config: (draft.style_config ?? {}) as Record<string, string>,
          planner_output: (draft.planner_output ?? {}) as Record<string, unknown>,
          response: String(draft.response ?? ""),
          raw_response: String(draft.raw_response ?? ""),
          safety_review: (draft.safety_review ?? {}) as Record<string, unknown>,
        })),
        selectedPersona:
          String(currentBatchItem.draft_candidates_json[0]?.draft_id ?? "") ||
          currentBatchItem.selected_persona_name ||
          currentBatchItem.selected_persona_names?.[0] ||
          null,
      });
    }
  }, [batchCurrentIndex, batchItems, currentBatchItem?.id, hydrateWorkspace, resetWorkspace]);

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

  function goToBatchIndex(nextIndex: number) {
    if (nextIndex < 0 || nextIndex >= visibleBatchItems.length) {
      return;
    }
    setBatchCurrentIndex(nextIndex);
  }

  function handleSelectBatchRow(rowNumber: number) {
    const index = visibleBatchItems.findIndex((item) => item.row_number === rowNumber);
    if (index >= 0) {
      setWorkspaceMode(isMailBatchMode ? "mail_batch" : "excel_batch");
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
    return {
      user_input: userInput,
      selected_persona_name: activeDraft?.persona_name ?? currentBatchItem?.selected_persona_name ?? selectedPersona ?? "",
      selected_persona_names: selectedPersonas,
      ai_selected_raw_response: activeDraft?.response ?? currentBatchItem?.ai_selected_raw_response ?? "",
      expert_polished_response: polishedText,
      expert_annotation: normalizedExpertAnnotation,
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
    setResponseEvaluation(EMPTY_EVALUATION);
    if (selectedPersonas.length === 0) {
      setStatusText("默认回信模型尚未加载完成，请稍后再试。");
      return;
    }
    await startGeneration({
      user_input: buildGenerationInput(userInput, currentWorkspaceContext),
      persona_names: selectedPersonas,
      compare_sources: false,
      source_mode: "auto",
    });
  }

  async function handlePersistBatchItem(status: string, recordId?: number | null) {
    if (!currentBatchItem || !activeDraft) {
      return;
    }

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
      sessionId: currentBatchItem.session_id as number,
      itemId: currentBatchItem.id as number,
      payload: {
        selected_persona_names: selectedPersonas,
        selected_persona_name: activeDraft.persona_name,
        selected_style_config: activeDraft.style_config,
        planner_output: activeDraft.planner_output,
        draft_candidates: drafts,
        ai_selected_raw_response: activeDraft.response,
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
        record_id: recordId ?? currentBatchItem.record_id ?? null,
        mail_thread_id: currentBatchItem.mail_thread_id ?? null,
        context: currentWorkspaceContext ?? currentBatchItem.context_json ?? {},
      },
    });

    if (detail.current_item_id) {
      const nextIndex = detail.items.findIndex((item) => item.id === detail.current_item_id);
      if (nextIndex >= 0) {
        setBatchCurrentIndex(nextIndex);
      }
    }
    return detail;
  }

  async function handleSave() {
    if (!activeDraft || !polishedText.trim()) {
      return;
    }

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
      ai_selected_raw_response: activeDraft.response,
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
      batch_session_id: currentBatchItem?.session_id ?? null,
      batch_item_id: currentBatchItem?.id ?? null,
    };

    try {
      const record = await saveRecord.mutateAsync(payload);
      if (currentBatchItem) {
        const detail = await handlePersistBatchItem("completed", record.id);
        const allDone = Boolean(detail && detail.total_items > 0 && detail.completed_items >= detail.total_items);
        if (allDone) {
          setStatusText(
            isMailBatchMode
              ? "这批人工书信已全部完成，最后一封回信已送达用户信箱，没有下一封待处理。"
              : "这批任务已全部完成，没有下一条待处理。",
          );
        } else {
          setStatusText(
            isMailBatchMode
              ? `当前回信已送达用户信箱，已进入下一封待处理书信。`
              : `第 ${currentBatchItem.row_number} 行已保存并写入历史记录，已进入下一条。`,
          );
        }
      } else {
        setStatusText("这条记录已经保存到历史库。");
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
      setWorkspaceMode("excel_batch");
      setBatchFileName(file.name);
      setStatusText(`已创建并持久化批量任务，共 ${result.total_items} 条。关闭网页后仍可继续处理。`);
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "Excel 导入失败");
    }
  }

  function handleSelectExcelBatchMode() {
    setWorkspaceMode("excel_batch");
    const excelSession = availableSessions.find((session) => session.source_file_name !== "assigned-mail-threads" && session.source_file_name !== "assigned-mail-thread");
    if (excelSession) {
      setActiveSessionId(excelSession.id);
      setStatusText("已切换到 Excel 批量任务。");
      return;
    }
    setActiveSessionId(null);
    resetWorkspace();
    setUserInput("");
    setPolishedText("");
    setBatchFileName(null);
    setStatusText("Excel 批量模式已启用，请在右侧上传 Excel 创建批量任务。");
  }

  async function handleLoadAssignedMailBatch() {
    setStatusText(null);
    try {
      const result = await createAssignedThreadsWorkspace.mutateAsync();
      setActiveSessionId(result.id);
      setWorkspaceMode("mail_batch");
      setBatchFileName("人工书信任务");
      setStatusText("已载入分配给你的人工书信任务。逐封生成、润色并保存后，会自动送达用户信箱。");
    } catch (error) {
      setWorkspaceMode("mail_batch");
      setStatusText(error instanceof Error ? error.message : "暂时没有可载入的人工书信任务。");
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
      if (!currentBatchItem) {
        const draftsFromRegenerate = await startGeneration({
          user_input: `${buildGenerationInput(userInput, currentWorkspaceContext)}\n\n【当前 AI 回复】\n${polishedText}\n\n【专家对当前 AI 回复的高亮批注】\n${sourceAnnotations
            .map(
              (annotation, index) =>
                `${index + 1}. 回复片段：${annotation.quote || "未填写"}；专家批注：${annotation.note || "未填写"}`,
            )
            .join("\n")}\n\n【专家总体说明】\n${expertAnnotation}`.trim(),
          persona_names: selectedPersonas.length > 0 ? selectedPersonas : [activeDraft?.persona_name ?? DEFAULT_PERSONA_NAME],
          compare_sources: false,
          source_mode: "auto",
        });

        const selectedDraft =
          draftsFromRegenerate.find((draft) => draft.draft_id === selectedPersona) ??
          draftsFromRegenerate[0] ??
          null;

        if (selectedDraft) {
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
            safety_review: selectedDraft.safety_review ?? {},
          };

          setResponseVersions([...existingVersions, nextVersion]);
          setActiveVersionIndex(nextVersion.version_index);
          setPolishedText(selectedDraft.response);
          setResponseEvaluation(EMPTY_EVALUATION);
          setSelectedPersona(selectedDraft.draft_id);
          setStatusText("已基于 AI 回复高亮批注重新生成，并新增一条可回退的回复版本。");
        }
        return;
      }

      const detail = await regenerateBatchSessionItem.mutateAsync({
        sessionId: currentBatchItem.session_id as number,
        itemId: currentBatchItem.id as number,
        payload: {
          selected_persona_name: activeDraft?.persona_name ?? currentBatchItem.selected_persona_name,
          selected_persona_names: selectedPersonas,
          source_annotations: sourceAnnotations,
          expert_annotation: expertAnnotation,
          current_response: polishedText,
          planner_output: activeDraft?.planner_output ?? currentBatchItem.planner_output_json ?? {},
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
            safety_review: (draft.safety_review ?? {}) as Record<string, unknown>,
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
          user_input: buildGenerationInput(userInput, currentWorkspaceContext),
          persona_name: activeDraft.persona_name,
          planner_output: plannerOutput,
          source_mode: "auto",
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
            safety_review: (draft.safety_review ?? {}) as Record<string, unknown>,
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
      safety_review: selectedDraft.safety_review ?? {},
    };

    updateDraftPlanner(selectedDraft.draft_id, selectedDraft.planner_output as PlannerOutput);
    setResponseVersions([...existingVersions, nextVersion]);
    setActiveVersionIndex(nextVersion.version_index);
    setPolishedText(selectedDraft.response);
    setResponseEvaluation(EMPTY_EVALUATION);
    setSelectedPersona(selectedDraft.draft_id);
  }

  async function handleRollbackVersion(versionIndex: number) {
    if (!currentBatchItem) {
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
        sessionId: currentBatchItem.session_id as number,
        itemId: currentBatchItem.id as number,
        versionIndex,
      });
      const updatedItem = detail.items.find((item) => item.id === currentBatchItem.id);
      if (updatedItem) {
        setResponseVersions(updatedItem.response_versions_json ?? []);
        setActiveVersionIndex(updatedItem.active_version_index ?? 0);
        setPolishedText(updatedItem.latest_response ?? polishedText);
        setSelectedPersonas(personas[0]?.name ? [personas[0].name] : selectedPersonas);
        setSourceAnnotations(updatedItem.source_annotations_json ?? sourceAnnotations);
        setResponseEvaluation(EMPTY_EVALUATION);
        setStatusText(`已回退到版本 ${versionIndex + 1}。`);
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "版本回退失败");
    }
  }

  return (
    <main className="min-h-screen px-3 py-4 md:px-6 xl:px-8">
      <div className="mx-auto max-w-[1760px]">
        <header className="surface-glow mb-4 overflow-hidden rounded-[22px] border border-white/70 bg-white/84 px-4 py-3 shadow-soft backdrop-blur">
          <div className="relative flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <img src={scirScLogo} alt="心灵笔友标志" className="h-14 w-20 shrink-0 object-contain mix-blend-multiply" />
              <div className="min-w-0">
                <h1 className="font-serif text-2xl text-ink md:text-3xl">
                  <span className="lilac-text">心灵笔友</span>
                </h1>
                <p className="mt-0.5 text-sm leading-6 text-ink/64">
                  咨询师 {user?.counselorId ?? "default"}
                  {isWorkspaceBatchMode && hasVisibleBatch ? ` · 批量 ${batchCompletedCount}/${visibleBatchItems.length}` : ""}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <div className="inline-flex rounded-full border border-line bg-white/72 p-1">
                <button
                  type="button"
                  onClick={() => setWorkspaceMode("single")}
                  className={`rounded-full px-3 py-1.5 text-sm transition ${
                    workspaceMode === "single" ? "lilac-gradient text-white shadow-card" : "text-ink/72"
                  }`}
                >
                  普通模式
                </button>
                <button
                  type="button"
                  onClick={handleSelectExcelBatchMode}
                  className={`rounded-full px-3 py-1.5 text-sm transition ${
                    workspaceMode === "excel_batch" ? "lilac-gradient text-white shadow-card" : "text-ink/72"
                  }`}
                >
                  Excel批量
                </button>
                <button
                  type="button"
                  onClick={handleLoadAssignedMailBatch}
                  disabled={createAssignedThreadsWorkspace.isPending}
                  className={`rounded-full px-3 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-45 ${
                    workspaceMode === "mail_batch" ? "lilac-gradient text-white shadow-card" : "text-ink/72"
                  }`}
                >
                  {createAssignedThreadsWorkspace.isPending ? "载入中..." : "人工书信"}
                </button>
              </div>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={jobLoading || selectedPersonas.length === 0 || !userInput.trim()}
                className="lilac-gradient inline-flex items-center justify-center gap-2 rounded-full px-5 py-2 text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45"
              >
                <Sparkles size={16} />
                {jobLoading ? "生成中..." : "生成回信草稿"}
              </button>
              <Link
                to="/records"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/70 px-4 py-2 text-sm text-ink transition hover:bg-paper/85"
              >
                <ScrollText size={16} />
                查看历史记录
              </Link>
              <button
                type="button"
                onClick={() => {
                  logout();
                  navigate("/login", { replace: true });
                }}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/70 px-4 py-2 text-sm text-ink transition hover:bg-paper/85"
              >
                <LogOut size={16} />
                退出登录
              </button>
            </div>
          </div>
        </header>

        <UserLetterPanel
          value={userInput}
          onChange={setUserInput}
          readOnly={Boolean(currentBatchItem)}
          compact
          batchMeta={
            currentBatchItem
              ? {
                  current: batchCurrentIndex + 1,
                  total: visibleBatchItems.length,
                  rowNumber: currentBatchItem.row_number,
                }
              : null
          }
        />

        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_390px] 2xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="grid gap-4">
            {statusText ? (
              <div className="rounded-[20px] border border-line bg-white/72 px-4 py-3 text-sm leading-7 text-moss shadow-card">
                {statusText}
              </div>
            ) : null}
            {jobError ? <p className="text-sm text-red-600">{jobError}</p> : null}

            <DraftStreamTabs
              drafts={drafts}
              selectedPersona={selectedPersona}
              onSelect={setSelectedPersona}
              displayName={getPersonaDisplayName}
            />

            <section className="grid gap-4 rounded-[22px] border border-line bg-white/76 p-4 shadow-soft md:p-5">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="font-serif text-2xl text-ink">
                  {getPersonaDisplayName(activeDraft?.persona_name ?? currentBatchItem?.selected_persona_name ?? DEFAULT_PERSONA_NAME)}
                </h2>
                <div className="rounded-full border border-line bg-paper/75 px-3 py-1.5 text-sm text-ink/72">
                  生成草稿 → 润色回信 → 保存
                </div>
              </div>
              <PolishingEditor
                value={polishedText}
                onChange={setPolishedText}
                annotations={sourceAnnotations}
                onAddAnnotation={handleAddSourceAnnotation}
                onRemoveAnnotation={handleRemoveSourceAnnotation}
              />
            </section>
          </div>

          <aside className="grid gap-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:self-start xl:overflow-y-auto xl:pr-1">
            <MailThreadContextPanel context={currentWorkspaceContext} />

            <PlannerInsightAccordion
              plannerOutput={activeDraft?.planner_output}
              onChange={handlePlannerChange}
              onRegenerate={handleRegenerateFromPlanner}
              regenerating={jobLoading || regenerateBatchSessionItem.isPending}
            />

            <ResponseEvaluationPanel
              value={responseEvaluation}
              onChange={setResponseEvaluation}
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
              canSave={Boolean(activeDraft && polishedText.trim()) && !(hasVisibleBatch && currentBatchItem?.status === "completed")}
              isSaving={saveRecord.isPending || updateBatchSessionItem.isPending}
              onSave={handleSave}
              batchMode={hasVisibleBatch}
              allCompleted={batchAllCompleted}
              isLastBatchItem={hasVisibleBatch && batchCurrentIndex >= visibleBatchItems.length - 1}
              onExportReviewedBatch={hasVisibleBatch ? handleExportReviewedBatch : null}
              exportingReviewedBatch={exportReviewedBatch.isPending}
            />

            {isWorkspaceBatchMode ? (
              <BatchExcelPanel
                importing={importBatchExcel.isPending || batchSessions.isLoading}
                fileName={batchFileName}
                items={visibleBatchItems}
                completedCount={batchCompletedCount}
                currentIndex={batchCurrentIndex}
                activeRowNumber={currentBatchItem?.row_number ?? null}
                completedRowNumbers={completedRowNumbers}
                mode={isMailBatchMode ? "mail" : "excel"}
                onImport={handleImportBatchExcel}
                onSelectRow={handleSelectBatchRow}
                onPrevious={() => goToBatchIndex(batchCurrentIndex - 1)}
                onNext={() => goToBatchIndex(batchCurrentIndex + 1)}
              />
            ) : null}
          </aside>
        </div>

      </div>
    </main>
  );
}
