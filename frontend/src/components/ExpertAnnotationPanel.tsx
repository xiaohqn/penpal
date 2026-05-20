type Props = {
  value: string;
  onChange: (value: string) => void;
  sampleReason: string;
  onSampleReasonChange: (value: string) => void;
};

export function ExpertAnnotationPanel({
  value,
  onChange,
  sampleReason,
  onSampleReasonChange,
}: Props) {
  return (
    <section className="rounded-[28px] border border-line bg-white/78 p-6 shadow-soft">
      <div className="mb-4">
        <p className="text-sm uppercase tracking-[0.22em] text-moss">专家批注</p>
        <h2 className="mt-2 font-serif text-3xl text-ink">记录修改理由与判断依据</h2>
        <p className="mt-2 text-sm leading-7 text-ink/68">
          这里适合写风格判断、风险提醒、为什么替换某些句子，后续导出 Excel 也会带上这部分。
        </p>
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="例如：原草稿共情到位，但建议偏泛；我强化了校园求助对象和一句能直接发出的开口话术。"
        className="min-h-[220px] w-full rounded-[28px] border border-transparent bg-paper/72 px-5 py-5 text-[15px] leading-8 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
      />
      <div className="mt-5 rounded-[24px] border border-line bg-paper/65 p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-ink/45">沉淀说明</p>
        <p className="mt-2 text-sm leading-7 text-ink/68">
          只要你在本条中留下专家批注或回复高亮批注，系统就会自动记录处理过程和最终满意版本，为后续 RAG 样本整理做准备。
        </p>
        <textarea
          value={sampleReason}
          onChange={(event) => onSampleReasonChange(event.target.value)}
          placeholder="可选：补一句这条样本为什么值得保留，例如“这条回复兼顾危机感知、共情承接和可执行建议”。"
          className="mt-3 min-h-[150px] w-full rounded-2xl border border-transparent bg-white/80 px-4 py-4 text-sm leading-7 text-ink outline-none transition focus:border-amber focus:shadow-[0_0_0_4px_rgba(79,110,140,0.12)]"
        />
      </div>
    </section>
  );
}
