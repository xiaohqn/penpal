import { Brain, Sparkles } from "lucide-react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  compact?: boolean;
  batchMeta?: {
    current: number;
    total: number;
    rowNumber: number;
  } | null;
  canGenerate?: boolean;
  generating?: boolean;
  useDeepThinking?: boolean;
  onToggleDeepThinking?: () => void;
  onGenerate?: () => void;
};

export function UserLetterPanel({
  value,
  onChange,
  readOnly = false,
  compact = false,
  batchMeta,
  canGenerate = false,
  generating = false,
  useDeepThinking = false,
  onToggleDeepThinking,
  onGenerate,
}: Props) {
  const lineCount = value.split("\n").reduce((total, line) => total + Math.max(1, Math.ceil(line.length / 38)), 0);
  const rows = compact ? 5 : Math.min(18, Math.max(8, lineCount + 2));

  return (
    <section className="rounded-panel border border-line bg-white/86 p-4 shadow-soft backdrop-blur md:p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 flex-col gap-2 md:flex-row md:items-center">
          <h2 className="font-serif text-xl text-ink md:text-2xl">用户来信</h2>
          {batchMeta ? (
            <div className="inline-flex w-fit items-center rounded-full bg-peach/55 px-3 py-1.5 text-sm text-ink/78">
              当前处理第 {batchMeta.current} / {batchMeta.total} 条，源 Excel 第 {batchMeta.rowNumber} 行
            </div>
          ) : null}
        </div>
        <div className="rounded-full bg-white/75 px-3 py-1 text-xs text-ink/50 shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
          {value.length} / 5000
        </div>
      </div>
      <div className="relative mt-3">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="输入来信内容"
          readOnly={readOnly}
          rows={rows}
          className="w-full resize-y rounded-[20px] border border-transparent bg-paper/75 px-4 py-3 pb-16 text-[15px] leading-8 text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)] read-only:bg-mist/45"
        />
        {onGenerate ? (
          <div className="absolute bottom-3 right-3 flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleDeepThinking}
              className={`inline-flex h-10 items-center gap-2 rounded-full border px-3 text-xs transition ${
                useDeepThinking
                  ? "border-amber bg-amber/12 text-ink shadow-card"
                  : "border-line bg-white/82 text-ink/62 hover:bg-white"
              }`}
            >
              <Brain size={15} />
              深度思考 {useDeepThinking ? "开" : "关"}
            </button>
            <button
              type="button"
              onClick={onGenerate}
              disabled={!canGenerate || generating}
              className="lilac-gradient inline-flex h-10 items-center justify-center gap-2 rounded-full px-4 text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45"
            >
              <Sparkles size={16} />
              {generating ? "生成中" : "生成"}
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
