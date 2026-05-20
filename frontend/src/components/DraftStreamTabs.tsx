import clsx from "clsx";

import type { DraftState } from "../features/generation/types";

type Props = {
  drafts: DraftState[];
  selectedPersona: string | null;
  onSelect: (draftId: string) => void;
};

export function DraftStreamTabs({ drafts, selectedPersona, onSelect }: Props) {
  if (drafts.length === 0) {
    return (
      <section className="rounded-panel border border-dashed border-line bg-white/62 p-6">
        <div className="inline-flex rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
          Step 2
        </div>
        <h2 className="mt-3 font-serif text-3xl text-ink">草稿比较区</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-ink/62">
          点击“生成多种草稿”后，这里会按风格展示流式生成过程。你可以快速横向比较，然后选一版进入润色。
        </p>
      </section>
    );
  }

  const current = drafts.find((item) => item.draft_id === selectedPersona) ?? drafts[0];

  return (
    <section className="rounded-panel border border-line bg-white/82 p-6 shadow-card backdrop-blur">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="inline-flex rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
            Step 2
          </div>
          <h2 className="mt-3 font-serif text-3xl text-ink">比较生成草稿并选择一版</h2>
          <p className="mt-2 text-sm leading-7 text-ink/66">
            已生成 {drafts.length} 个候选草稿。切换不同标签即可查看风格差异，选中的一版会自动带入下方润色区。
          </p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/80 px-4 py-3 text-sm text-ink/72">
          当前查看 <span className="font-semibold text-ink">{current.persona_name}</span>
          <span className="ml-2 rounded-full bg-white/75 px-2 py-1 text-xs text-ink/62">{current.source_label}</span>
        </div>
      </div>
      <div className="mb-5 flex flex-wrap gap-3">
        {drafts.map((draft) => {
          const active = draft.draft_id === current.draft_id;
          return (
            <button
              key={draft.draft_id}
              type="button"
              onClick={() => onSelect(draft.draft_id)}
              className={clsx(
                "rounded-full border px-4 py-2 text-sm transition",
                active
                  ? "border-amber bg-amber text-white shadow-card"
                  : "border-line bg-white/78 text-ink/80 hover:border-amber/50 hover:bg-paper/85",
              )}
            >
              {draft.persona_name} · {draft.source_label}
              {draft.status === "streaming" ? " · 生成中" : draft.status === "error" ? " · 出错" : " · 已完成"}
            </button>
          );
        })}
      </div>
      <article className="rounded-[28px] border border-line bg-paper/72 px-6 py-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-amber">当前草稿</p>
            <h3 className="mt-2 text-xl font-semibold text-ink">
              {current.persona_name} · {current.source_label}
            </h3>
          </div>
          <span
            className={clsx(
              "rounded-full px-3 py-1 text-xs",
              current.status === "error"
                ? "bg-red-100 text-red-700"
                : current.status === "streaming"
                  ? "bg-peach/55 text-ink"
                  : "bg-moss/20 text-ink",
            )}
          >
            {current.status === "streaming" ? "正在流式生成" : current.status === "error" ? "生成失败" : "可进入润色"}
          </span>
        </div>
        {current.error ? (
          <p className="text-sm text-red-600">{current.error}</p>
        ) : (
          <div className="min-h-[320px] whitespace-pre-wrap text-[15px] leading-8 text-ink">
            {current.response || "正在生成..."}
          </div>
        )}
      </article>
    </section>
  );
}
