type Props = {
  styleConfig?: Record<string, string>;
};

const styleKeys = [
  ["narrative", "叙事"],
  ["advice", "建议"],
  ["empathy", "共情"],
  ["cognitive", "认知"],
] as const;

export function ToneGuideBar({ styleConfig }: Props) {
  if (!styleConfig) {
    return null;
  }

  return (
    <section className="rounded-[28px] border border-line bg-paper/68 p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-moss">当前风格标签</p>
          <h3 className="mt-1 text-lg font-semibold text-ink">润色时保持这组气质不跑偏</h3>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {styleKeys.map(([key, label]) => (
          <div key={key} className="rounded-2xl border border-line bg-white/72 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-ink/42">{label}</p>
            <p className="mt-2 text-sm text-ink/84">{styleConfig[key] ?? "未定义"}</p>
          </div>
      ))}
      </div>
    </section>
  );
}
