/**
 * 输入：
 * - result：后端返回的完整安全检测结果，包含原始风险类型、风险原因、安全回复正文、需高亮的安全片段，以及高亮来源。
 * - selectedRiskLabels：当前页面展示并允许人工修正的风险类型列表。
 * - onRiskLabelsChange：当用户在修正面板中改动风险类型时，把最新选择回传给页面级状态。
 * - selectedSafetyResponseSource / onSafetyResponseSourceChange：
 *   对比模式下当前选中的安全回复候选来源，以及切换候选后的页面级状态回写回调。
 * - safetyPolishedText / onSafetyPolishedTextChange：安全回复专家润色区的当前文本和回写回调。
 * - safetySourceAnnotations / onAddSafetySourceAnnotation / onRemoveSafetySourceAnnotation：
 *   安全回复润色区里针对当前回复留下的片段批注，以及新增 / 删除批注的页面级回写回调。
 * - safetyExpertAnnotation / onSafetyExpertAnnotationChange：
 *   安全回复整体修改说明，以及编辑该说明时的页面级回写回调。
 * - isSafetyPolishVisible / onToggleSafetyPolish：控制安全回复专家润色区是否展开。
 * - safetyDialogueEvaluation / onSafetyDialogueEvaluationChange：
 *   安全对话四维评分结果，以及评分变化时的页面级回写回调。
 * - canRegenerateSafetyReply / isRegeneratingSafetyReply / onRegenerateSafetyReply / safetyRegenerateStatusText：
 *   控制安全回复“按批注重生成”按钮的可用状态、请求状态与结果提示。
 * - canSaveSafetyRecord / isSavingSafetyRecord / onSaveSafetyRecord / safetySaveStatusText：
 *   控制安全回复记录保存条的状态与行为。
 * - onBack：从安全回复结果页返回工作台主页。
 * 输出：
 * - 渲染安全回复结果页，并提供风险类型人工修正入口、安全回复人工润色入口与整体说明重生成入口。
 * 作用：
 * - 这个组件负责展示不安全来信的兜底回复，同时让人工可以在前端直接修正风险类别，并基于安全回复说明快速迭代新版本。
 */
import { useState } from "react";
import { RefreshCcw } from "lucide-react";

import { PolishingEditor } from "./PolishingEditor";
import { SaveRecordBar } from "./SaveRecordBar";
import { SafetyDialogueEvaluationPanel } from "./SafetyDialogueEvaluationPanel";
import type {
  SafetyCheckResponse,
  SafetyDialogueEvaluation,
  SafetyResponseCandidate,
} from "../features/safety/types";
import type { SourceAnnotation } from "../features/records/types";

const AVAILABLE_RISK_LABELS = [
  "安全",
  "自杀倾向",
  "针对他人的暴力或伤害倾向",
  "非自杀性自伤行为",
  "严重的物质滥用",
  "严重的进食障碍",
  "疑似精神病性症状",
  "卷入高危活动或畸形关系",
] as const;

type Props = {
  result: SafetyCheckResponse;
  selectedRiskLabels: string[];
  onRiskLabelsChange: (labels: string[]) => void;
  selectedSafetyResponseSource: string | null;
  onSafetyResponseSourceChange: (source: string) => void;
  safetyPolishedText: string;
  onSafetyPolishedTextChange: (value: string) => void;
  safetySourceAnnotations: SourceAnnotation[];
  onAddSafetySourceAnnotation: (annotation: SourceAnnotation) => void;
  onRemoveSafetySourceAnnotation: (annotationId: string) => void;
  safetyExpertAnnotation: string;
  onSafetyExpertAnnotationChange: (value: string) => void;
  isSafetyPolishVisible: boolean;
  onToggleSafetyPolish: () => void;
  safetyDialogueEvaluation: SafetyDialogueEvaluation;
  onSafetyDialogueEvaluationChange: (value: SafetyDialogueEvaluation) => void;
  canRegenerateSafetyReply: boolean;
  isRegeneratingSafetyReply: boolean;
  onRegenerateSafetyReply: () => void;
  safetyRegenerateStatusText?: string | null;
  canSaveSafetyRecord: boolean;
  isSavingSafetyRecord: boolean;
  onSaveSafetyRecord: () => void;
  safetySaveStatusText?: string | null;
  onBack: () => void;
};

type HighlightPart = {
  text: string;
  isHighlighted: boolean;
};

function isBuiltInRiskLabel(label: string): label is (typeof AVAILABLE_RISK_LABELS)[number] {
  return AVAILABLE_RISK_LABELS.includes(label as (typeof AVAILABLE_RISK_LABELS)[number]);
}

function getNextRiskLabels(
  label: (typeof AVAILABLE_RISK_LABELS)[number],
  currentLabels: string[],
): string[] {
  if (label === "安全") {
    return ["安全"];
  }

  const labelsWithoutSafe = currentLabels.filter((item) => item !== "安全");
  const labelAlreadySelected = labelsWithoutSafe.includes(label);

  if (labelAlreadySelected) {
    const remainingLabels = labelsWithoutSafe.filter((item) => item !== label);
    return remainingLabels.length > 0 ? remainingLabels : ["安全"];
  }

  return [...labelsWithoutSafe, label];
}

function buildSafeReplyHighlightParts(
  safeResponse: string,
  safeHighlightSegments: string[] | undefined,
): HighlightPart[] {
  const normalizedSegments = Array.from(
    new Set((safeHighlightSegments ?? []).map((segment) => segment.trim()).filter(Boolean)),
  );

  if (!safeResponse || normalizedSegments.length === 0) {
    return [{ text: safeResponse, isHighlighted: false }];
  }

  const parts: HighlightPart[] = [];
  let cursor = 0;

  for (const segment of normalizedSegments) {
    const matchIndex = safeResponse.indexOf(segment, cursor);
    if (matchIndex < 0) {
      continue;
    }

    if (matchIndex > cursor) {
      parts.push({
        text: safeResponse.slice(cursor, matchIndex),
        isHighlighted: false,
      });
    }

    parts.push({
      text: segment,
      isHighlighted: true,
    });
    cursor = matchIndex + segment.length;
  }

  if (cursor < safeResponse.length) {
    parts.push({
      text: safeResponse.slice(cursor),
      isHighlighted: false,
    });
  }

  return parts.length > 0 ? parts : [{ text: safeResponse, isHighlighted: false }];
}

function getActiveSafetyCandidate(
  result: SafetyCheckResponse,
  selectedSafetyResponseSource: string | null,
): SafetyResponseCandidate | null {
  const candidates = result.safe_response_candidates ?? [];
  if (candidates.length === 0) {
    return null;
  }

  if (selectedSafetyResponseSource) {
    const matchedCandidate = candidates.find(
      (candidate) => candidate.source === selectedSafetyResponseSource,
    );
    if (matchedCandidate) {
      return matchedCandidate;
    }
  }

  return candidates[0] ?? null;
}

export function SafetyResultPanel({
  result,
  selectedRiskLabels,
  onRiskLabelsChange,
  selectedSafetyResponseSource,
  onSafetyResponseSourceChange,
  safetyPolishedText,
  onSafetyPolishedTextChange,
  safetySourceAnnotations,
  onAddSafetySourceAnnotation,
  onRemoveSafetySourceAnnotation,
  safetyExpertAnnotation,
  onSafetyExpertAnnotationChange,
  isSafetyPolishVisible,
  onToggleSafetyPolish,
  safetyDialogueEvaluation,
  onSafetyDialogueEvaluationChange,
  canRegenerateSafetyReply,
  isRegeneratingSafetyReply,
  onRegenerateSafetyReply,
  safetyRegenerateStatusText = null,
  canSaveSafetyRecord,
  isSavingSafetyRecord,
  onSaveSafetyRecord,
  safetySaveStatusText = null,
  onBack,
}: Props) {
  const [isEditingRiskLabels, setIsEditingRiskLabels] = useState(false);
  const [customRiskLabelDraft, setCustomRiskLabelDraft] = useState("");
  const customRiskLabels = selectedRiskLabels.filter((label) => !isBuiltInRiskLabel(label));
  const activeSafetyCandidate = getActiveSafetyCandidate(result, selectedSafetyResponseSource);
  const safeReplyText =
    activeSafetyCandidate?.safe_response ?? result.safe_response ?? "未生成安全回复。";
  const safeReplyHighlightParts = buildSafeReplyHighlightParts(
    safeReplyText,
    activeSafetyCandidate?.safe_highlight_segments ?? result.safe_highlight_segments,
  );
  const hasHighlightedSafetySegments = safeReplyHighlightParts.some((part) => part.isHighlighted);
  const activeHighlightSource =
    activeSafetyCandidate?.safe_highlight_source ?? result.safe_highlight_source;
  const highlightSourceLabel =
    activeHighlightSource === "llm"
      ? "大模型提取"
      : activeHighlightSource === "fallback"
        ? "兜底规则"
        : null;
  const candidateCount = result.safe_response_candidates?.length ?? 0;

  function handleRiskLabelToggle(label: (typeof AVAILABLE_RISK_LABELS)[number]) {
    onRiskLabelsChange(getNextRiskLabels(label, selectedRiskLabels));
  }

  function handleCustomRiskLabelRemove(label: string) {
    const remainingLabels = selectedRiskLabels.filter((item) => item !== label);
    onRiskLabelsChange(remainingLabels.length > 0 ? remainingLabels : ["安全"]);
  }

  function handleCustomRiskLabelSubmit() {
    const trimmedLabel = customRiskLabelDraft.trim();
    if (!trimmedLabel) {
      return;
    }

    const standardRiskLabels = selectedRiskLabels.filter(
      (label) => isBuiltInRiskLabel(label) && label !== "安全",
    );
    onRiskLabelsChange([...standardRiskLabels, trimmedLabel]);
    setCustomRiskLabelDraft("");
  }

  return (
    <section className="grid gap-5 rounded-panel border border-line bg-white/78 p-6 shadow-soft backdrop-blur">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-moss">安全回复结果</p>
          <h2 className="mt-1 font-serif text-3xl text-ink">检测到需要优先处理的风险信号</h2>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-ink/72">
            当前来信不适合继续进入常规人格草稿流程，建议先使用安全回复进行承接。
          </p>
        </div>
        <button
          type="button"
          onClick={onBack}
          className="rounded-full border border-line bg-paper/70 px-5 py-3 text-sm text-ink transition hover:bg-white"
        >
          返回初始页面
        </button>
      </div>

      <section className="rounded-3xl border border-line bg-paper/70 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-amber">风险类型</p>
            {isEditingRiskLabels ? (
              <p className="mt-2 text-sm leading-6 text-ink/68">
                可以从这 8 类标准情况里任选其一或多项，也可以在“其它”里输入自定义风险；如果只保留“安全”，其余风险会自动清空。
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => setIsEditingRiskLabels((current) => !current)}
            className="rounded-full border border-line bg-paper/70 px-4 py-2 text-sm text-ink transition hover:bg-white"
          >
            {isEditingRiskLabels ? "完成修正" : "修正"}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {selectedRiskLabels.map((label) =>
            isEditingRiskLabels ? (
              <button
                key={label}
                type="button"
                onClick={() =>
                  isBuiltInRiskLabel(label)
                    ? handleRiskLabelToggle(label)
                    : handleCustomRiskLabelRemove(label)
                }
                className="rounded-full border border-peach/50 bg-peach/35 px-3 py-1 text-sm text-ink transition hover:bg-peach/55"
              >
                {label}
              </button>
            ) : (
              <span key={label} className="rounded-full bg-peach/35 px-3 py-1 text-sm text-ink">
                {label}
              </span>
            ),
          )}
        </div>
        {isEditingRiskLabels ? (
          <>
            <div className="mt-4 flex flex-wrap gap-2">
              {AVAILABLE_RISK_LABELS.map((label) => {
                const isSelected = selectedRiskLabels.includes(label);

                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => handleRiskLabelToggle(label)}
                    className={`rounded-full px-3 py-2 text-sm transition ${
                      isSelected
                        ? "border border-moss bg-moss text-white"
                        : "border border-line bg-white/75 text-ink hover:bg-paper/85"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            <div className="mt-4 grid gap-3 rounded-2xl border border-dashed border-line bg-white/55 p-4 md:grid-cols-[1fr_auto]">
              <div>
                <p className="text-sm text-ink/75">其它</p>
                <input
                  type="text"
                  value={customRiskLabelDraft}
                  onChange={(event) => setCustomRiskLabelDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      handleCustomRiskLabelSubmit();
                    }
                  }}
                  placeholder="其它"
                  className="mt-2 w-full rounded-2xl border border-line bg-white/85 px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-moss"
                />
                {customRiskLabels.length > 0 ? (
                  <p className="mt-2 text-xs leading-5 text-ink/55">
                    当前其它项：{customRiskLabels.join(" / ")}
                  </p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={handleCustomRiskLabelSubmit}
                disabled={!customRiskLabelDraft.trim()}
                className="rounded-full bg-ink px-4 py-3 text-sm text-paper transition disabled:cursor-not-allowed disabled:bg-ink/30"
              >
                加入风险类型
              </button>
            </div>
          </>
        ) : null}
      </section>

      <section className="rounded-3xl border border-line bg-paper/70 p-5">
        <p className="text-xs uppercase tracking-[0.18em] text-amber">风险原因</p>
        <div className="mt-3 whitespace-pre-wrap text-[15px] leading-7 text-ink">{result.reason}</div>
      </section>

      <section className="rounded-3xl border border-line bg-paper/70 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-amber">安全回复</p>
            {activeSafetyCandidate ? (
              <p className="mt-2 text-sm leading-6 text-ink/68">
                当前正在查看：{activeSafetyCandidate.source_label}
              </p>
            ) : null}
            {hasHighlightedSafetySegments ? (
              <p className="mt-2 text-sm leading-6 text-ink/68">
                与现实求助、自我保护直接相关的关键安全建议已高亮，方便快速定位。
              </p>
            ) : null}
            {highlightSourceLabel ? (
              <p className="mt-1 text-xs leading-5 text-ink/55">
                当前高亮来源：{highlightSourceLabel}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onToggleSafetyPolish}
            className="rounded-full border border-line bg-paper/70 px-4 py-2 text-sm text-ink transition hover:bg-white"
          >
            {isSafetyPolishVisible ? "收起专家润色" : "专家润色"}
          </button>
        </div>
        {candidateCount > 1 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {(result.safe_response_candidates ?? []).map((candidate) => {
              const isActive = activeSafetyCandidate?.source === candidate.source;

              return (
                <button
                  key={candidate.source}
                  type="button"
                  onClick={() => onSafetyResponseSourceChange(candidate.source)}
                  className={`rounded-full border px-4 py-2 text-sm transition ${
                    isActive
                      ? "border-moss bg-moss/12 text-moss"
                      : "border-line bg-white/80 text-ink hover:bg-paper"
                  }`}
                >
                  {candidate.source_label}
                </button>
              );
            })}
          </div>
        ) : null}
        {activeSafetyCandidate?.intent ?? result.intent ? (
          <div className="mt-4 rounded-2xl border border-line/80 bg-white/78 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-ink/48">风险意图总结</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-ink/78">
              {activeSafetyCandidate?.intent ?? result.intent}
            </p>
          </div>
        ) : null}
        <div className="mt-3 whitespace-pre-wrap text-[15px] leading-7 text-ink">
          {safeReplyHighlightParts.map((part, index) =>
            part.isHighlighted ? (
              <mark
                key={`${part.text}-${index}`}
                className="rounded-md bg-amber/25 px-1 py-0.5 text-ink shadow-[inset_0_-0.45em_0_rgba(217,119,6,0.12)]"
              >
                {part.text}
              </mark>
            ) : (
              <span key={`${part.text}-${index}`}>{part.text}</span>
            ),
          )}
        </div>
      </section>

      <SafetyDialogueEvaluationPanel
        value={safetyDialogueEvaluation}
        onChange={onSafetyDialogueEvaluationChange}
      />

      {isSafetyPolishVisible ? (
        <div className="grid gap-5">
          <PolishingEditor
            value={safetyPolishedText}
            onChange={onSafetyPolishedTextChange}
            annotations={safetySourceAnnotations}
            onAddAnnotation={onAddSafetySourceAnnotation}
            onRemoveAnnotation={onRemoveSafetySourceAnnotation}
            eyebrow="安全回复润色区"
            title="先复制安全回复，再由专家继续修改成能直接发出的版本"
            placeholder="点击“专家润色”后，这里会先带入安全回复内容，供继续修改。"
            showAnnotations
          />
          <section className="rounded-[28px] border border-line bg-white/78 p-6 shadow-soft">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.22em] text-moss">说明驱动重生成</p>
                <h2 className="mt-2 font-serif text-3xl text-ink">按当前安全回复说明生成新版本</h2>
                <p className="mt-2 max-w-3xl text-sm leading-7 text-ink/68">
                  先在上面的安全回复里划词并填写片段批注，再补充整体修改说明。新版本会优先处理这些被标记的片段，同时保留安全边界和现实求助建议。
                </p>
              </div>
              <button
                type="button"
                onClick={onRegenerateSafetyReply}
                disabled={!canRegenerateSafetyReply || isRegeneratingSafetyReply}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-amber px-5 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45"
              >
                <RefreshCcw size={16} />
                {isRegeneratingSafetyReply ? "重生成中..." : "按说明重生成"}
              </button>
            </div>
            <textarea
              value={safetyExpertAnnotation}
              onChange={(event) => onSafetyExpertAnnotationChange(event.target.value)}
              placeholder="例如：这版风险承接够了，但现实求助建议还不够具体；请补一句能直接发给老师或家长的开口方式。"
              className="mt-5 min-h-[180px] w-full rounded-[28px] border border-transparent bg-paper/72 px-5 py-5 text-[15px] leading-8 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
            />
            {safetyRegenerateStatusText ? (
              <div className="mt-4 rounded-[24px] border border-line bg-paper/70 px-4 py-4 text-sm leading-7 text-ink/72">
                {safetyRegenerateStatusText}
              </div>
            ) : null}
          </section>
        </div>
      ) : null}

      <SaveRecordBar
        canSave={canSaveSafetyRecord}
        isSaving={isSavingSafetyRecord}
        onSave={onSaveSafetyRecord}
        description="保存后会把原始来信、风险类型、修正类型、风险原因、原始回复和润色回复一起入库。"
        buttonLabel="保存安全回复记录"
        statusText={safetySaveStatusText}
      />
    </section>
  );
}
