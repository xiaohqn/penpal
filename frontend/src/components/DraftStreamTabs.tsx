import clsx from "clsx";

import type { DraftState } from "../features/generation/types";

type Props = {
  drafts: DraftState[];
  selectedPersona: string | null;
  onSelect: (draftId: string) => void;
  displayName?: (personaName: string) => string;
};

export function DraftStreamTabs({ drafts, selectedPersona, onSelect, displayName = (personaName) => personaName }: Props) {
  if (drafts.length === 0) {
    return null;
  }

  const current = drafts.find((item) => item.draft_id === selectedPersona) ?? drafts[0];
  const currentSafety = getSafetyMeta(current.safety_review);
  const currentPersonaLabel = displayName(current.persona_name);
  const statusLabel =
    current.status === "streaming" ? "生成中" : current.status === "error" ? "出错" : "已生成";

  return (
    <details className="group rounded-[18px] border border-line bg-white/72 px-4 py-3 shadow-card backdrop-blur">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-ink">AI 原稿</span>
          <span className="rounded-full bg-paper/85 px-2.5 py-1 text-xs text-ink/62">
            {currentPersonaLabel} · {current.source_label}
          </span>
          <span
            className={clsx(
              "rounded-full px-2.5 py-1 text-xs",
              current.status === "error"
                ? "bg-red-100 text-red-700"
                : current.status === "streaming"
                  ? "bg-peach/55 text-ink"
                  : "bg-moss/20 text-ink",
            )}
          >
            {statusLabel}
          </span>
        </div>
        <span className="text-xs text-ink/50 transition group-open:hidden">展开</span>
        <span className="hidden text-xs text-ink/50 transition group-open:inline">收起</span>
      </summary>
      {drafts.length > 1 ? <div className="mt-3 flex flex-wrap gap-2">
        {drafts.map((draft) => {
          const active = draft.draft_id === current.draft_id;
          return (
            <button
              key={draft.draft_id}
              type="button"
              onClick={() => onSelect(draft.draft_id)}
              className={clsx(
                "rounded-full border px-3 py-1.5 text-sm transition",
                active
                  ? "border-amber bg-amber text-white shadow-card"
                  : "border-line bg-white/78 text-ink/80 hover:border-amber/50 hover:bg-paper/85",
              )}
            >
              {displayName(draft.persona_name)} · {draft.source_label}
              {draft.status === "streaming" ? " · 生成中" : draft.status === "error" ? " · 出错" : " · 已完成"}
            </button>
          );
        })}
      </div> : null}
      <article className="mt-3 rounded-[16px] border border-line bg-paper/72 px-4 py-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-ink">
              {currentPersonaLabel} · {current.source_label}
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
          {currentSafety ? (
            <span className={clsx("rounded-full px-3 py-1 text-xs", currentSafety.className)}>
              {currentSafety.label}
            </span>
          ) : null}
        </div>
        {currentSafety && current.safety_review?.signals?.length ? (
          <div className="mb-5 rounded-[16px] border border-line bg-white/70 p-4 text-sm leading-7 text-ink/72">
            <p className="font-semibold text-ink">安全审核提示</p>
            {current.safety_review.signals.slice(0, 3).map((signal) => (
              <p key={signal}>• {signal}</p>
            ))}
            {current.safety_review.replacement_used ? (
              <p className="mt-2 text-red-700">原始草稿命中高风险表达，已替换为安全回应，请咨询师人工复核。</p>
            ) : null}
          </div>
        ) : null}
        {current.error ? (
          <p className="text-sm text-red-600">{current.error}</p>
        ) : (
          <div className="whitespace-pre-wrap text-[15px] leading-7 text-ink">
            {current.response || "正在生成..."}
          </div>
        )}
      </article>
    </details>
  );
}

function getSafetyMeta(review: DraftState["safety_review"]) {
  if (!review) return null;
  if (review.replacement_used || review.blocked) {
    return { label: "安全审核：已替换", className: "bg-red-100 text-red-700" };
  }
  if (review.risk_level && review.risk_level !== "NONE") {
    return { label: `安全审核：${review.risk_level}`, className: "bg-[#FFF7ED] text-[#C2410C]" };
  }
  return { label: "安全审核通过", className: "bg-[#ECFDF5] text-[#047857]" };
}
