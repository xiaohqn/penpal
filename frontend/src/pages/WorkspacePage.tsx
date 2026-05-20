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
import { ResponseVersionPanel } from "../components/ResponseVersionPanel";
import { SaveRecordBar } from "../components/SaveRecordBar";
import { ToneGuideBar } from "../components/ToneGuideBar";
import { UserLetterPanel } from "../components/UserLetterPanel";
import { useGenerationWorkspace, usePersonas } from "../features/generation/hooks";
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
  ReviewedBatchItem,
  SourceAnnotation,
} from "../features/records/types";

const DEFAULT_INPUT = `这段时间我过得特别难受。每天早上想到要去学校，心里就沉甸甸的，很害怕。我不是不想学习，但上课时总控制不住地分心，总担心同学在背后议论我。放学我也尽量绕路，躲开那几个经常堵我的同学。

这些事压得我快喘不过气了。我试过想跟爸妈或者别人说，但话到嘴边又说不出来，怕没人信，也怕情况变得更糟。现在晚上经常失眠，躲在被子里哭，白天还要强撑着，感觉特别累，好像下一秒就要垮掉。

我真的不知道该怎么办了，感觉自己快扛不住了。您能给我一点建议吗？`;

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
      active_version_index: item.active_version_index,
    }))
    .sort((a, b) => a.row_number - b.row_number);
}

export function WorkspacePage() {
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
    resetWorkspace,
    hydrateWorkspace,
  } = useGenerationWorkspace();
  const saveRecord = useSaveRecord();
  const importBatchExcel = useImportBatchExcel();
  const updateBatchSessionItem = useUpdateBatchSessionItem();
  const regenerateBatchSessionItem = useRegenerateBatchSessionItem();
  const rollbackBatchSessionItem = useRollbackBatchSessionItem();
  const exportReviewedBatch = useExportReviewedBatch();

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
        source_annotations_json: item.source_annotations_json,
        response_versions_json: item.response_versions_json,
        active_version_index: item.active_version_index,
        status: item.status,
        record_id: item.record_id,
      })),
    [sessionDetail?.items],
  );

  const [userInput, setUserInput] = useState(DEFAULT_INPUT);
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>([]);
  const [polishedText, setPolishedText] = useState("");
  const [expertAnnotation, setExpertAnnotation] = useState("");
  const [sampleReason, setSampleReason] = useState("");
  const [statusText, setStatusText] = useState<string | null>(null);
  const [batchFileName, setBatchFileName] = useState<string | null>(null);
  const [batchCurrentIndex, setBatchCurrentIndex] = useState(0);
  const [workspaceMode, setWorkspaceMode] = useState<"single" | "batch">("single");
  const [generationSourceMode, setGenerationSourceMode] = useState<"auto" | "api" | "vllm" | "compare">("compare");
  const [sourceAnnotations, setSourceAnnotations] = useState<SourceAnnotation[]>([]);
  const [responseVersions, setResponseVersions] = useState<ResponseVersion[]>([]);
  const [activeVersionIndex, setActiveVersionIndex] = useState(0);
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
  const batchCompletedCount = batchItems.filter((item) => item.status === "completed").length;
  const batchAllCompleted = isBatchMode && batchCompletedCount === batchItems.length;
  const completedRowNumbers = batchItems.filter((item) => item.status === "completed").map((item) => item.row_number);
  const reviewedBatchItems = buildReviewedItems(sessionDetail?.items ?? []);

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
    if (!currentBatchItem) {
      return;
    }

    resetWorkspace();
    setUserInput(currentBatchItem.user_input);
    setSelectedPersonas(currentBatchItem.selected_persona_names ?? []);
    setSourceAnnotations(currentBatchItem.source_annotations_json ?? []);
    setResponseVersions(currentBatchItem.response_versions_json ?? []);
    setActiveVersionIndex(currentBatchItem.active_version_index ?? 0);
    setExpertAnnotation(currentBatchItem.expert_annotation ?? "");
    setSampleReason(currentBatchItem.sample_reason ?? "");
    setPolishedText(currentBatchItem.latest_response ?? "");
    setStatusText(
      currentBatchItem.status === "completed"
        ? `已恢复第 ${batchCurrentIndex + 1} / ${batchItems.length} 条，当前为已完成状态，可回看版本或继续修改。`
        : `已恢复第 ${batchCurrentIndex + 1} / ${batchItems.length} 条，请继续处理。`,
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
    return {
      user_input: userInput,
      selected_persona_name: activeDraft?.persona_name ?? currentBatchItem?.selected_persona_name ?? selectedPersona ?? "",
      selected_persona_names: selectedPersonas,
      ai_selected_raw_response: activeDraft?.response ?? currentBatchItem?.ai_selected_raw_response ?? "",
      expert_polished_response: polishedText,
      expert_annotation: normalizedExpertAnnotation,
      sample_reason: normalizedSampleReason,
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
    if (selectedPersonas.length === 0) {
      setStatusText("请先选择至少一种风格，再生成草稿。");
      return;
    }
    await startGeneration({
      user_input: userInput,
      persona_names: selectedPersonas,
      compare_sources: generationSourceMode === "compare",
      source_mode: generationSourceMode,
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
        sample_reason: sampleReason,
        sample_snapshot: buildSampleSnapshot(),
        source_annotations: sourceAnnotations,
        response_versions: nextVersions,
        active_version_index: activeVersionIndex,
        status,
        record_id: recordId ?? currentBatchItem.record_id ?? null,
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
      sample_reason: sampleReason,
      sample_snapshot: buildSampleSnapshot(),
      source_annotations: sourceAnnotations,
      response_versions: nextVersions,
      batch_session_id: currentBatchItem?.session_id ?? null,
      batch_item_id: currentBatchItem?.id ?? null,
    };

    try {
      const record = await saveRecord.mutateAsync(payload);
      setStatusText(
        currentBatchItem
          ? `第 ${currentBatchItem.row_number} 行已保存并写入历史记录，已同步更新到持久批次。`
          : "这条记录已经保存到历史库。",
      );
      if (currentBatchItem) {
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
      if (!currentBatchItem) {
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
          setActiveVersionIndex(nextVersion.version_index);
          setPolishedText(selectedDraft.response);
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
        setStatusText("已基于 AI 回复高亮批注重新生成，并新增一条可回退的回复版本。");
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "批注重生成失败");
    }
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
        setSelectedPersonas(updatedItem.selected_persona_names_json ?? selectedPersonas);
        setSourceAnnotations(updatedItem.source_annotations_json ?? sourceAnnotations);
        setStatusText(`已回退到版本 ${versionIndex + 1}。`);
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "版本回退失败");
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
                  onClick={() => setWorkspaceMode("batch")}
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
                onClick={handleRegenerateFromAnnotations}
                disabled={!currentBatchItem || regenerateBatchSessionItem.isPending}
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
              readOnly={Boolean(currentBatchItem)}
              batchMeta={
                currentBatchItem
                  ? {
                      current: batchCurrentIndex + 1,
                      total: batchItems.length,
                      rowNumber: currentBatchItem.row_number,
                    }
                  : null
              }
            />
          </div>

          <div className="grid gap-6">
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

            <PlannerInsightAccordion plannerOutput={activeDraft?.planner_output} />

            <section className="grid gap-5 rounded-panel border border-line bg-white/76 p-6 shadow-soft">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.22em] text-moss">Step 3 & 4</p>
                  <h2 className="mt-2 font-serif text-3xl text-ink">
                    {activeDraft?.persona_name ?? currentBatchItem?.selected_persona_name ?? "先选择一份草稿"}
                  </h2>
                  <p className="mt-2 text-sm leading-7 text-ink/66">
                    先对选中的草稿做最终润色，再记录本次人工判断与修改原因，方便后续复盘和高质量数据沉淀。
                  </p>
                </div>
                <div className="rounded-[24px] border border-line bg-paper/75 px-4 py-3 text-sm text-ink/72">
                  当前工作流：生成草稿 → 润色回复并高亮批注 → 基于批注重生成 → 保存
                </div>
              </div>
              <ToneGuideBar styleConfig={activeDraft?.style_config ?? currentBatchItem?.selected_style_config_json} />
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
                batchMode={isBatchMode}
                allCompleted={batchAllCompleted}
                onExportReviewedBatch={isBatchMode ? handleExportReviewedBatch : null}
                exportingReviewedBatch={exportReviewedBatch.isPending}
              />
            </section>
          </div>

          {isWorkspaceBatchMode ? (
            <div className="grid gap-6">
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
            </div>
          ) : null}
        </div>

      </div>
    </main>
  );
}
