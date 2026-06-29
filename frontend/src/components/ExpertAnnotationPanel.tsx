type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function ExpertAnnotationPanel({
  value,
  onChange,
}: Props) {
  return (
    <section className="rounded-[22px] border border-line bg-white/78 p-4 shadow-soft">
      <div className="mb-3">
        <p className="text-xs uppercase tracking-[0.18em] text-moss">专家批注</p>
        <h2 className="mt-1 font-serif text-xl text-ink">修改理由与判断依据</h2>
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="例如：原草稿共情到位，但建议偏泛；我强化了校园求助对象和一句能直接发出的开口话术。"
        className="min-h-[120px] w-full rounded-[18px] border border-transparent bg-paper/72 px-4 py-3 text-[15px] leading-7 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
      />
    </section>
  );
}
