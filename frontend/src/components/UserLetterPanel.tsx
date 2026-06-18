type Props = {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  batchMeta?: {
    current: number;
    total: number;
    rowNumber: number;
  } | null;
};

export function UserLetterPanel({ value, onChange, readOnly = false, batchMeta }: Props) {
  const lineCount = value.split("\n").reduce((total, line) => total + Math.max(1, Math.ceil(line.length / 38)), 0);
  const rows = Math.min(18, Math.max(8, lineCount + 2));

  return (
    <section className="rounded-panel border border-line bg-white/80 p-6 shadow-soft backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
            Context
          </div>
          <h2 className="mt-3 font-serif text-3xl text-ink">原始来信</h2>
          {batchMeta ? (
            <div className="mt-4 inline-flex items-center rounded-full bg-peach/55 px-4 py-2 text-sm text-ink/78">
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
        className="mt-5 w-full resize-none rounded-[28px] border border-transparent bg-paper/75 px-5 py-5 text-[15px] leading-8 text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
      />
    </section>
  );
}
