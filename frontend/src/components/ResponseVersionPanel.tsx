import clsx from "clsx";
import { GitBranchPlus, RotateCcw } from "lucide-react";

import type { ResponseVersion } from "../features/records/types";

type Props = {
  versions: ResponseVersion[];
  activeVersionIndex: number;
  canRegenerate: boolean;
  regenerating: boolean;
  onRegenerate: () => void;
  onRollback: (versionIndex: number) => void;
};

export function ResponseVersionPanel({
  versions,
  activeVersionIndex,
  canRegenerate,
  regenerating,
  onRegenerate,
  onRollback,
}: Props) {
  return (
    <section className="rounded-[28px] border border-line bg-white/78 p-6 shadow-soft">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-moss">版本管理</p>
          <h2 className="mt-2 font-serif text-3xl text-ink">基于批注重生成并随时回退</h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/68">
            AI 回复里的高亮批注和专家说明会被纳入新的生成上下文。系统会保留每次回复版本，便于专家不满意时快速回退。
          </p>
        </div>
        <button
          type="button"
          onClick={onRegenerate}
          disabled={!canRegenerate || regenerating}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-amber px-5 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45"
        >
          <GitBranchPlus size={16} />
          {regenerating ? "重生成中..." : "基于批注重新生成"}
        </button>
      </div>

      {versions.length > 0 ? (
        <div className="mt-5 grid gap-3">
          {versions
            .slice()
            .sort((a, b) => b.version_index - a.version_index)
            .map((version) => {
              const isActive = version.version_index === activeVersionIndex;
              return (
                <div
                  key={`${version.version_index}-${version.created_at}`}
                  className={clsx(
                    "rounded-[24px] border px-4 py-4",
                    isActive ? "border-amber bg-[rgba(79,110,140,0.08)]" : "border-line bg-paper/72",
                  )}
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-ink">{version.label || `版本 ${version.version_index + 1}`}</span>
                        <span className="rounded-full bg-white/75 px-2 py-1 text-xs text-ink/64">
                          {version.source === "annotation_regenerate" ? "批注重生成" : version.source}
                        </span>
                        {isActive ? (
                          <span className="rounded-full bg-amber px-2 py-1 text-xs text-white">当前生效</span>
                        ) : null}
                      </div>
                      <p className="mt-2 text-xs uppercase tracking-[0.16em] text-ink/42">
                        {version.selected_persona_name || "未标记风格"} · {version.created_at || "未记录时间"}
                      </p>
                      <p className="mt-3 line-clamp-3 whitespace-pre-wrap text-sm leading-7 text-ink/74">
                        {version.response}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => onRollback(version.version_index)}
                      disabled={isActive}
                      className="inline-flex items-center gap-2 rounded-full border border-line bg-white/75 px-4 py-2 text-sm text-ink transition hover:bg-paper/78 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <RotateCcw size={15} />
                      回退到此版本
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      ) : (
        <div className="mt-5 rounded-[24px] border border-dashed border-line bg-paper/68 px-4 py-5 text-sm leading-7 text-ink/62">
          当前还没有版本历史。完成一轮保存或基于批注重新生成后，这里会开始记录每次回复版本。
        </div>
      )}
    </section>
  );
}
