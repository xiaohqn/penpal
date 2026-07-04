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
};

export function UserLetterPanel({ value, onChange, readOnly = false, compact = false, batchMeta }: Props) {
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
        <div className="rounded-full bg-white/75 px-3 py-1 text-sm text-ink/55 shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
          {value.length} / 5000
        </div>
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="输入来信内容，支持较长文本。"
        readOnly={readOnly}
        rows={rows}
        className="mt-3 w-full resize-y rounded-[20px] border border-transparent bg-paper/75 px-4 py-3 text-sm leading-7 text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
      />
    </section>
  );
}
