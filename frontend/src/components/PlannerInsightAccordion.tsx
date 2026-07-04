import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { PlannerOutput } from "../features/generation/types";

type Props = {
  plannerOutput?: PlannerOutput;
  onChange?: (plannerOutput: PlannerOutput) => void;
  onRegenerate?: (plannerOutput: PlannerOutput) => void;
  regenerating?: boolean;
};

const TEXT_FIELDS: Array<{ key: keyof PlannerOutput; label: string }> = [
  { key: "intention", label: "意图与需求" },
  { key: "core_issue", label: "核心问题" },
  { key: "wrong_but_easy_answer", label: "容易写偏" },
  { key: "value_guidance", label: "价值观引导" },
  { key: "risk_assessment", label: "风险判断" },
  { key: "generation_plan", label: "生成大纲" },
];

export function PlannerInsightAccordion({ plannerOutput, onChange, onRegenerate, regenerating = false }: Props) {
  const [draftPlanner, setDraftPlanner] = useState<PlannerOutput>({});
  const [ragModalOpen, setRagModalOpen] = useState(false);

  useEffect(() => {
    const nextPlanner = stripStoryPlan(plannerOutput ?? {});
    setDraftPlanner(nextPlanner);
  }, [plannerOutput]);

  if (!plannerOutput || Object.keys(plannerOutput).length === 0) {
    return null;
  }

  const ragReferences = draftPlanner.rag_references ?? [];

  function syncPlanner(nextPlanner: PlannerOutput) {
    setDraftPlanner(nextPlanner);
  }

  function updateTextField(key: keyof PlannerOutput, value: string) {
    syncPlanner({ ...draftPlanner, [key]: value });
  }

  function handleRegenerateFromPlanner() {
    const parsed = stripStoryPlan(draftPlanner);
    onChange?.(parsed);
    onRegenerate?.(parsed);
  }

  return (
    <section className="rounded-panel border border-line bg-white/74 p-5 shadow-card">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-moss">Planner</p>
          <h3 className="mt-1 font-serif text-2xl text-ink">核心判断与大纲</h3>
        </div>
        <button
          type="button"
          onClick={handleRegenerateFromPlanner}
          disabled={!onRegenerate || regenerating}
          className="self-start rounded-full bg-amber px-4 py-2 text-xs font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45 md:self-center"
        >
          {regenerating ? "重生成中..." : "按 Planner 重生成全文"}
        </button>
      </div>
      <div className="mt-5 grid gap-3 text-sm leading-7 text-ink/82">
        {TEXT_FIELDS.map((field) => (
          <section
            key={field.key}
            className="rounded-[18px] border border-transparent bg-paper/42 px-3 py-3 transition focus-within:border-amber/40 focus-within:bg-white/78 focus-within:shadow-[0_0_0_4px_rgba(79,110,140,0.08)]"
          >
            <label htmlFor={`planner-${String(field.key)}`} className="mb-1 block text-xs uppercase tracking-[0.18em] text-amber">
              {field.label}
            </label>
            <PlannerInlineTextarea
              id={`planner-${String(field.key)}`}
              value={String(draftPlanner[field.key] ?? "")}
              onChange={(value) => updateTextField(field.key, value)}
            />
          </section>
        ))}
        <section className="rounded-[18px] border border-line bg-paper/56 px-3 py-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-amber">RAG 参考样本</p>
              <p className="mt-1 text-xs text-ink/50">
                {ragReferences.length > 0 ? `已引用 ${ragReferences.length} 条` : "本次未引用样本"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setRagModalOpen(true)}
              disabled={ragReferences.length === 0}
              className="self-start rounded-full border border-line bg-white/78 px-4 py-2 text-xs font-medium text-ink transition hover:bg-paper/80 disabled:cursor-not-allowed disabled:text-ink/36 md:self-center"
            >
              {ragReferences.length > 0 ? `查看 RAG 参考（已引用 ${ragReferences.length} 条）` : "暂无 RAG 参考"}
            </button>
          </div>
        </section>
      </div>
      <RagReferenceModal
        open={ragModalOpen}
        references={ragReferences}
        onClose={() => setRagModalOpen(false)}
      />
    </section>
  );
}

function PlannerInlineTextarea({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useLayoutEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      id={id}
      ref={textareaRef}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      rows={1}
      className="block min-h-[2rem] w-full resize-none overflow-hidden rounded-xl border border-transparent bg-transparent px-1 py-1 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/34 focus:bg-paper/66"
    />
  );
}

function RagReferenceModal({
  open,
  references,
  onClose,
}: {
  open: boolean;
  references: NonNullable<PlannerOutput["rag_references"]>;
  onClose: () => void;
}) {
  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center px-3 py-4 md:px-6">
      <button
        type="button"
        aria-label="关闭 RAG 参考弹窗"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-ink/24 backdrop-blur-[2px]"
      />
      <section className="relative flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-[26px] border border-line bg-white shadow-[0_24px_90px_rgba(31,40,51,0.24)]">
        <header className="flex flex-col gap-3 border-b border-line bg-paper/74 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-amber">RAG References</p>
            <h3 className="mt-1 font-serif text-2xl text-ink">参考样本对比</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="self-start rounded-full border border-line bg-white px-4 py-2 text-sm text-ink transition hover:bg-paper/80 md:self-center"
          >
            关闭
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          {references.length > 0 ? (
            <div className="grid gap-5">
              {references.map((reference, index) => (
                <article
                  key={`${reference.source ?? "sample"}-${reference.record_id ?? index}`}
                  className="rounded-[22px] border border-line bg-paper/56 p-4"
                >
                  <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-mist px-3 py-1 text-ink/72">
                      参考 {index + 1}
                    </span>
                    <span className="rounded-full bg-white/78 px-3 py-1 text-ink/72">
                      来源：{reference.source === "seed" ? "现场种子库" : "专家记录"}
                    </span>
                    <span className="rounded-full bg-white/78 px-3 py-1 text-ink/62">
                      分数：{typeof reference.score === "number" ? reference.score.toFixed(3) : "暂无"}
                    </span>
                    <span className="rounded-full bg-white/78 px-3 py-1 text-ink/62">
                      风格：{reference.selected_persona_name || "暂无"}
                    </span>
                    {typeof reference.record_id === "number" ? (
                      <span className="rounded-full bg-white/78 px-3 py-1 text-ink/62">
                        ID：{reference.record_id}
                      </span>
                    ) : null}
                  </div>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <section className="max-h-[52vh] overflow-y-auto rounded-[18px] border border-line bg-white/78 p-4">
                      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-ink/42">相似来信</p>
                      <p className="whitespace-pre-wrap text-sm leading-7 text-ink/80">
                        {reference.user_input_full || reference.user_input_excerpt || "暂无"}
                      </p>
                    </section>
                    <section className="max-h-[52vh] overflow-y-auto rounded-[18px] border border-line bg-white/78 p-4">
                      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-ink/42">参考回复</p>
                      <p className="whitespace-pre-wrap text-sm leading-7 text-ink/80">
                        {reference.expert_response_full || reference.expert_response_excerpt || "暂无"}
                      </p>
                    </section>
                  </div>
                  {reference.expert_annotation_full || reference.expert_annotation ? (
                    <section className="mt-4 rounded-[18px] border border-line bg-white/78 p-4">
                      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-ink/42">专家批注</p>
                      <p className="whitespace-pre-wrap text-sm leading-7 text-ink/80">
                        {reference.expert_annotation_full || reference.expert_annotation}
                      </p>
                    </section>
                  ) : null}
                  <details className="mt-4 rounded-[18px] border border-line bg-white/62 p-4">
                    <summary className="cursor-pointer text-xs uppercase tracking-[0.14em] text-ink/48">
                      查看标签
                    </summary>
                    <pre className="mt-3 max-h-60 overflow-auto rounded-xl bg-paper/80 p-3 text-xs leading-5 text-ink/72">
{JSON.stringify(
  {
    sample_tags: reference.sample_tags ?? {},
    planner_labels: reference.planner_labels ?? {},
  },
  null,
  2,
)}
                    </pre>
                  </details>
                </article>
              ))}
            </div>
          ) : (
            <p className="rounded-[18px] border border-line bg-paper/72 px-4 py-3 text-sm text-ink/62">
              本次没有足够相似的样本，因此未附加 few-shot。
            </p>
          )}
        </div>
      </section>
    </div>,
    document.body,
  );
}

function stripStoryPlan(plannerOutput: PlannerOutput): PlannerOutput {
  const {
    story_plan: _storyPlan,
    surface_issue: _surfaceIssue,
    positive_motive: _positiveMotive,
    persona_strategy: _personaStrategy,
    response_focus: _responseFocus,
    action_strategy: _actionStrategy,
    sample_words: _sampleWords,
    must_include: _mustInclude,
    must_avoid: _mustAvoid,
    ...rest
  } = plannerOutput as PlannerOutput & {
    story_plan?: unknown;
    surface_issue?: unknown;
    positive_motive?: unknown;
    persona_strategy?: unknown;
    response_focus?: unknown;
    action_strategy?: unknown;
    sample_words?: unknown;
    must_include?: unknown;
    must_avoid?: unknown;
  };
  const normalized = { ...rest };
  const aliases = plannerOutput as PlannerOutput & {
    generation_plan?: unknown;
    reply_outline?: unknown;
    outline?: unknown;
    plan?: unknown;
    writing_plan?: unknown;
    response_plan?: unknown;
  };
  normalized.generation_plan = renderPlannerText(
    aliases.generation_plan ?? aliases.reply_outline ?? aliases.outline ?? aliases.plan ?? aliases.writing_plan ?? aliases.response_plan,
  );
  return normalized;
}

function renderPlannerText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value.trim();
  if (Array.isArray(value)) {
    return value.map(renderPlannerText).filter(Boolean).join("\n");
  }
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>).map(renderPlannerText).filter(Boolean).join("\n");
  }
  return String(value).trim();
}
