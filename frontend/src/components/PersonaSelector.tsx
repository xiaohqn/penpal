import clsx from "clsx";
import { CheckCircle2, Sparkles } from "lucide-react";

import type { PersonaCatalogItem } from "../features/generation/types";

type Props = {
  personas: PersonaCatalogItem[];
  selected: string[];
  onToggle: (personaName: string) => void;
};

const stylePreview = [
  ["empathy", "共情"],
  ["narrative", "叙事"],
  ["cognitive", "认知"],
  ["advice", "建议"],
] as const;

export function PersonaSelector({ personas, selected, onToggle }: Props) {
  return (
    <section className="rounded-panel border border-line bg-white/82 p-6 shadow-card backdrop-blur">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
            <Sparkles size={14} />
            Step 1
          </div>
          <h2 className="mt-3 font-serif text-3xl text-ink">选择要比较的 AI 专家风格</h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/68">
            推荐一次勾选 2 到 3 个风格进行横向对比。卡片展示的是每种人格的写作气质，而不是固定模板。
          </p>
        </div>
        <div className="rounded-[24px] border border-line bg-paper/80 px-4 py-3 text-sm text-ink/74">
          已选择 <span className="font-semibold text-ink">{selected.length}</span> 种风格
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {personas.map((persona) => {
          const active = selected.includes(persona.name);
          return (
            <button
              key={persona.name}
              type="button"
              onClick={() => onToggle(persona.name)}
              className={clsx(
                "group rounded-[28px] border p-5 text-left transition focus:outline-none",
                active
                  ? "border-amber bg-[rgba(79,110,140,0.08)] shadow-card"
                  : "border-line bg-white/84 hover:-translate-y-0.5 hover:border-amber/55 hover:bg-white",
              )}
            >
              <div className="flex items-center justify-between">
                <div>
                  <strong className="text-base text-ink">{persona.name}</strong>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-ink/42">
                    专家风格卡
                  </p>
                </div>
                <span
                  className={clsx(
                    "inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs",
                    active ? "bg-amber text-white" : "bg-mist text-ink/70",
                  )}
                >
                  {active ? <CheckCircle2 size={14} /> : null}
                  {active ? "已加入" : "点击选择"}
                </span>
              </div>
              <p className="mt-3 min-h-[72px] text-sm leading-7 text-ink/72">{persona.blurb}</p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {stylePreview.map(([key, label]) => (
                  <div
                    key={key}
                    className={clsx(
                      "rounded-2xl border px-3 py-2 text-xs leading-5",
                      active ? "border-white/40 bg-white/55 text-ink/82" : "border-line bg-paper/72 text-ink/68",
                    )}
                  >
                    <p className="uppercase tracking-[0.16em] text-ink/42">{label}</p>
                    <p className="mt-1 text-sm text-ink/80">{persona.style_config[key] ?? "未定义"}</p>
                  </div>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
