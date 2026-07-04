import { useState } from "react";
import { Highlighter, Plus } from "lucide-react";

import type { SourceAnnotation } from "../features/records/types";

type Props = {
  value: string;
  onChange: (value: string) => void;
  annotations?: SourceAnnotation[];
  onAddAnnotation?: ((annotation: SourceAnnotation) => void) | null;
  onRemoveAnnotation?: ((annotationId: string) => void) | null;
};

export function PolishingEditor({
  value,
  onChange,
  annotations = [],
  onAddAnnotation = null,
  onRemoveAnnotation = null,
}: Props) {
  const [annotationNote, setAnnotationNote] = useState("");
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number; quote: string } | null>(null);

  function handleSelection(event: React.SyntheticEvent<HTMLTextAreaElement>) {
    const target = event.currentTarget;
    const start = target.selectionStart ?? 0;
    const end = target.selectionEnd ?? 0;
    const quote = value.slice(start, end).trim();
    if (end > start && quote) {
      setSelectionRange({ start, end, quote });
    }
  }

  function handleAddAnnotation() {
    if (!selectionRange || !onAddAnnotation) {
      return;
    }

    onAddAnnotation({
      id: `${Date.now()}-${selectionRange.start}-${selectionRange.end}`,
      start: selectionRange.start,
      end: selectionRange.end,
      quote: selectionRange.quote,
      note: annotationNote.trim(),
      color: "amber",
    });
    setAnnotationNote("");
    setSelectionRange(null);
  }

  return (
    <section className="rounded-[22px] border border-line bg-white/78 p-4 shadow-soft md:p-5">
      <div className="mb-3 flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-amber">回信编辑</p>
          <h2 className="mt-1 font-serif text-2xl text-ink">AI 原稿与专家润色区</h2>
        </div>
        <p className="text-sm text-ink/58">选中文字可添加批注并重生成</p>
      </div>

      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onSelect={handleSelection}
        placeholder="生成草稿后，这里会自动带入内容，供继续润色。"
        className="min-h-[520px] w-full rounded-[20px] border border-transparent bg-paper/72 px-5 py-4 text-[15px] leading-8 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
      />

      <section className="mt-4 rounded-[20px] border border-line bg-paper/68 p-4">
        <details open={Boolean(selectionRange || annotations.length)}>
          <summary className="cursor-pointer list-none">
            <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-2">
                <Highlighter size={16} className="text-amber" />
                <p className="text-sm uppercase tracking-[0.18em] text-amber">高亮批注</p>
              </div>
              <p className="text-xs text-ink/50">{annotations.length ? `${annotations.length} 条批注` : "可折叠"}</p>
            </div>
          </summary>

          {selectionRange ? (
            <div className="mt-4 rounded-[18px] border border-amber/35 bg-white/82 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-ink/42">当前选中回复片段</p>
              <p className="mt-2 rounded-2xl bg-paper/85 px-3 py-3 text-sm leading-7 text-ink">{selectionRange.quote}</p>
              <textarea
                value={annotationNote}
                onChange={(event) => setAnnotationNote(event.target.value)}
                placeholder="例如：这句太空泛、这里需要更温柔、这里要补一个更具体的建议。"
                className="mt-3 min-h-[88px] w-full rounded-2xl border border-transparent bg-paper/72 px-4 py-3 text-sm leading-7 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.12)]"
              />
              <div className="mt-3 flex gap-3">
                <button
                  type="button"
                  onClick={handleAddAnnotation}
                  className="inline-flex items-center gap-2 rounded-full bg-amber px-4 py-2 text-sm text-white transition hover:-translate-y-0.5"
                >
                  <Plus size={15} />
                  添加批注
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectionRange(null);
                    setAnnotationNote("");
                  }}
                  className="rounded-full border border-line bg-white/75 px-4 py-2 text-sm text-ink"
                >
                  取消
                </button>
              </div>
            </div>
          ) : null}

          {annotations.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {annotations.map((annotation, index) => (
                <div key={annotation.id} className="rounded-[18px] border border-line bg-white/82 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em] text-ink/42">批注 {index + 1}</p>
                      <p className="mt-2 rounded-2xl bg-paper/85 px-3 py-2 text-sm leading-7 text-ink">
                        {annotation.quote || "未记录回复片段"}
                      </p>
                      <p className="mt-2 text-sm leading-7 text-ink/74">{annotation.note || "暂无说明"}</p>
                    </div>
                    {onRemoveAnnotation ? (
                      <button
                        type="button"
                        onClick={() => onRemoveAnnotation(annotation.id)}
                        className="rounded-full border border-line bg-paper/75 px-3 py-1 text-xs text-ink"
                      >
                        删除
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : null}

        </details>
      </section>
    </section>
  );
}
