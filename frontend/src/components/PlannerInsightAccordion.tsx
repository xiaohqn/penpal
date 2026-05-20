import type { PlannerOutput } from "../features/generation/types";

type Props = {
  plannerOutput?: PlannerOutput;
};

export function PlannerInsightAccordion({ plannerOutput }: Props) {
  if (!plannerOutput || Object.keys(plannerOutput).length === 0) {
    return null;
  }

  return (
    <details className="rounded-panel border border-line bg-white/74 p-5 shadow-card">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.22em] text-moss">AI 思考过程</p>
            <h3 className="mt-1 font-serif text-2xl text-ink">查看 Planner 的意图分析与大纲</h3>
          </div>
          <p className="text-sm text-ink/58">展开后可看到风险判断、人格策略和段落计划</p>
        </div>
      </summary>
      <div className="mt-5 grid gap-4 text-sm leading-7 text-ink/82 md:grid-cols-2">
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">意图分析</p>
          <p>{plannerOutput.intent_analysis || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">风险判断</p>
          <p>{plannerOutput.risk_assessment || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">人格策略</p>
          <p>{plannerOutput.persona_strategy || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-amber">生成大纲</p>
          <p>{plannerOutput.generation_plan || "暂无"}</p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/70 p-4 md:col-span-2">
          <p className="mb-3 text-xs uppercase tracking-[0.18em] text-amber">段落计划</p>
          <ul className="grid gap-2">
            {(plannerOutput.paragraph_plan ?? []).map((item) => (
              <li key={item} className="rounded-2xl bg-white/68 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}
