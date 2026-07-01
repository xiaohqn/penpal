import clsx from "clsx";
import { GitBranchPlus } from "lucide-react";

import type { ResponseVersion } from "../features/records/types";

type Props = {
  versions: ResponseVersion[];
  activeVersionIndex: number;
  canRegenerate: boolean;
  regenerating: boolean;
  onRegenerate: () => void;
  onRollback: (versionIndex: number) => void;
};

function formatVersionTime(value: string) {
  if (!value) {
    return "未记录时间";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function ResponseVersionPanel({
  versions,
  activeVersionIndex,
  canRegenerate,
  regenerating,
  onRegenerate,
  onRollback,
}: Props) {
  return (
    <section className="rounded-[22px] border border-line bg-white/78 p-4 shadow-soft">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-moss">版本管理</p>
          <h2 className="mt-1 font-serif text-xl text-ink">局部修订</h2>
        </div>
        <button
          type="button"
          onClick={onRegenerate}
          disabled={!canRegenerate || regenerating}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-amber px-4 py-2 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45"
        >
          <GitBranchPlus size={16} />
          {regenerating ? "改写中..." : "局部应用批注"}
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
                        {isActive ? (
                          <span className="rounded-full bg-amber px-2 py-1 text-xs text-white">当前生效</span>
                        ) : null}
                      </div>
                      <p className="mt-2 text-xs uppercase tracking-[0.16em] text-ink/42">
                        {formatVersionTime(version.created_at)}
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
                      回退
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      ) : (
        <div className="mt-4 rounded-[18px] border border-dashed border-line bg-paper/68 px-4 py-4 text-sm leading-7 text-ink/62">
          暂无版本历史。
        </div>
      )}
    </section>
  );
}
