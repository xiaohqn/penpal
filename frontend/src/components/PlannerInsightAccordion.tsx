import { useEffect, useState } from "react";

import type { PlannerOutput } from "../features/generation/types";

type Props = {
  plannerOutput?: PlannerOutput;
  onChange?: (plannerOutput: PlannerOutput) => void;
  onRegenerate?: (plannerOutput: PlannerOutput) => void;
  regenerating?: boolean;
};

export function PlannerInsightAccordion({ plannerOutput, onChange, onRegenerate, regenerating = false }: Props) {
  const [draftText, setDraftText] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    const nextPlanner = stripStoryPlan(plannerOutput ?? {});
    setDraftText(JSON.stringify(nextPlanner, null, 2));
    setEditError(null);
  }, [plannerOutput]);

  if (!plannerOutput || Object.keys(plannerOutput).length === 0) {
    return null;
  }

  const displayPlanner = stripStoryPlan(plannerOutput);
  const intention = displayPlanner.intention || displayPlanner.intent_analysis || "暂无";
  const ragReferences = displayPlanner.rag_references ?? [];

  function parseDraft() {
    try {
      const parsed = stripStoryPlan(JSON.parse(draftText) as PlannerOutput);
      setDraftText(JSON.stringify(parsed, null, 2));
      setEditError(null);
      return parsed;
    } catch {
      setEditError("Planner JSON 格式不正确，请检查引号、逗号和括号。");
      return null;
    }
  }

  function handleApplyPlannerEdit() {
    const parsed = parseDraft();
    if (!parsed) {
      return;
    }
    onChange?.(parsed);
  }

  function handleRegenerateFromPlanner() {
    const parsed = parseDraft();
    if (!parsed) {
      return;
    }
    onChange?.(parsed);
    onRegenerate?.(parsed);
  }

  return (
    <details className="rounded-panel border border-line bg-white/74 p-5 shadow-card">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.22em] text-moss">AI 思考过程</p>
            <h3 className="mt-1 font-serif text-2xl text-ink">查看 Planner 的核心判断与大纲</h3>
          </div>
          <p className="text-sm text-ink/58">展开后可看到问题本质、写偏风险和行动话术</p>
        </div>
      </summary>
      <div className="mt-5 grid gap-4 text-sm leading-7 text-ink/82 md:grid-cols-2">
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">意图与需求</p>
          <p>{intention}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">表层问题</p>
          <p>{displayPlanner.surface_issue || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">核心问题</p>
          <p>{displayPlanner.core_issue || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">容易写偏</p>
          <p>{displayPlanner.wrong_but_easy_answer || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">正面动机</p>
          <p>{displayPlanner.positive_motive || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">价值观引导</p>
          <p>{displayPlanner.value_guidance || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">风险判断</p>
          <p>{displayPlanner.risk_assessment || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">人格策略</p>
          <p>{displayPlanner.persona_strategy || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">生成大纲</p>
          <p>{displayPlanner.generation_plan || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4 md:col-span-2">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">回复重点</p>
          <p>{displayPlanner.response_focus || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.18em] text-amber">下一步</p>
          <ul className="grid gap-2">
            {(displayPlanner.action_strategy ?? []).map((item) => (
              <li key={item} className="rounded-2xl bg-white/68 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.18em] text-amber">可用话术</p>
          <ul className="grid gap-2">
            {(displayPlanner.sample_words ?? []).map((item) => (
              <li key={item} className="rounded-2xl bg-white/68 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4 md:col-span-2">
          <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="text-xs uppercase tracking-[0.18em] text-amber">编辑 Planner JSON</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleApplyPlannerEdit}
                disabled={!onChange}
                className="rounded-full border border-line bg-white/75 px-4 py-2 text-xs text-ink transition hover:bg-paper/80 disabled:cursor-not-allowed disabled:opacity-45"
              >
                应用修改
              </button>
              <button
                type="button"
                onClick={handleRegenerateFromPlanner}
                disabled={!onRegenerate || regenerating}
                className="rounded-full bg-amber px-4 py-2 text-xs font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45"
              >
                {regenerating ? "重生成中..." : "按 Planner 重生成全文"}
              </button>
            </div>
          </div>
          <textarea
            value={draftText}
            onChange={(event) => setDraftText(event.target.value)}
            className="min-h-[320px] w-full rounded-2xl border border-transparent bg-white/80 px-4 py-4 font-mono text-xs leading-6 text-ink outline-none transition focus:border-amber focus:shadow-[0_0_0_4px_rgba(79,110,140,0.12)]"
          />
          {editError ? <p className="mt-2 text-sm text-red-600">{editError}</p> : null}
        </div>

        <details className="rounded-[24px] border border-line bg-paper/70 p-4 md:col-span-2">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <p className="text-xs uppercase tracking-[0.18em] text-amber">RAG 参考样本</p>
              <p className="text-xs text-ink/50">
                {ragReferences.length > 0 ? `已引用 ${ragReferences.length} 条，点击展开查看` : "本次未引用样本"}
              </p>
            </div>
          </summary>
          <div className="mt-3">
            {ragReferences.length > 0 ? (
              <div className="grid gap-3">
                {ragReferences.map((reference, index) => (
                  <article
                    key={`${reference.source ?? "sample"}-${reference.record_id ?? index}`}
                    className="rounded-2xl border border-line bg-white/70 p-4"
                  >
                    <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
                      <span className="rounded-full bg-mist px-3 py-1 text-ink/72">
                        来源：{reference.source === "seed" ? "现场种子库" : "专家记录"}
                      </span>
                      <span className="rounded-full bg-paper px-3 py-1 text-ink/62">
                        分数：{typeof reference.score === "number" ? reference.score.toFixed(3) : "暂无"}
                      </span>
                      <span className="rounded-full bg-paper px-3 py-1 text-ink/62">
                        风格：{reference.selected_persona_name || "暂无"}
                      </span>
                      {typeof reference.record_id === "number" ? (
                        <span className="rounded-full bg-paper px-3 py-1 text-ink/62">
                          ID：{reference.record_id}
                        </span>
                      ) : null}
                    </div>
                    <div className="grid gap-3 lg:grid-cols-2">
                      <section className="rounded-xl bg-paper/68 px-3 py-3">
                        <p className="mb-1 text-xs uppercase tracking-[0.14em] text-ink/42">相似来信</p>
                        <p className="whitespace-pre-wrap">{reference.user_input_excerpt || "暂无"}</p>
                      </section>
                      <section className="rounded-xl bg-paper/68 px-3 py-3">
                        <p className="mb-1 text-xs uppercase tracking-[0.14em] text-ink/42">参考回复</p>
                        <p className="whitespace-pre-wrap">{reference.expert_response_excerpt || "暂无"}</p>
                      </section>
                    </div>
                    {reference.expert_annotation ? (
                      <section className="mt-3 rounded-xl bg-paper/68 px-3 py-3">
                        <p className="mb-1 text-xs uppercase tracking-[0.14em] text-ink/42">专家批注</p>
                        <p className="whitespace-pre-wrap">{reference.expert_annotation}</p>
                      </section>
                    ) : null}
                    <details className="mt-3">
                      <summary className="cursor-pointer text-xs uppercase tracking-[0.14em] text-ink/48">
                        查看标签
                      </summary>
                      <pre className="mt-2 max-h-56 overflow-auto rounded-xl bg-paper/80 p-3 text-xs leading-5 text-ink/72">
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
              <p className="rounded-2xl bg-white/68 px-3 py-2 text-ink/62">
                系统会在历史满意稿或种子库中找到相似内容时自动引用参考样本；本次没有足够相似的样本，因此未附加 few-shot。
              </p>
            )}
          </div>
        </details>
      </div>
    </details>
  );
}

function stripStoryPlan(plannerOutput: PlannerOutput): PlannerOutput {
  const { story_plan: _storyPlan, ...rest } = plannerOutput as PlannerOutput & { story_plan?: unknown };
  return rest;
}
