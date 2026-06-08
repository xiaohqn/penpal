/**
 * 输入：
 * - value：当前编辑器里展示的正文内容。
 * - onChange：当用户修改润色内容时，把最新文本回传给父组件。
 * - annotations / onAddAnnotation / onRemoveAnnotation：可选的高亮批注数据与操作回调。
 * - eyebrow / title / placeholder：可选的文案覆盖项，用于在不同业务场景下复用同一套编辑器。
 * - showAnnotations：控制是否显示“AI 回复高亮批注”区域。
 * - sidePanel：可选的并排侧栏内容，用于把评价或补充信息固定在编辑区旁边。
 * 输出：
 * - 渲染一个可编辑的大文本润色区域，并在需要时附带高亮批注能力。
 * 作用：
 * - 这个组件统一承载“专家对 AI 初稿做人工编辑”的交互，既能服务普通人格草稿，也能服务安全回复场景。
 */
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Highlighter, Plus } from "lucide-react";

import type { SourceAnnotation } from "../features/records/types";

type Props = {
  value: string;
  onChange: (value: string) => void;
  annotations?: SourceAnnotation[];
  onAddAnnotation?: ((annotation: SourceAnnotation) => void) | null;
  onRemoveAnnotation?: ((annotationId: string) => void) | null;
  eyebrow?: string;
  title?: string;
  placeholder?: string;
  showAnnotations?: boolean;
  sidePanel?: ReactNode;
};

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function PolishingEditor({
  value,
  onChange,
  annotations = [],
  onAddAnnotation = null,
  onRemoveAnnotation = null,
  eyebrow = "Step 3",
  title = "专家润色区",
  placeholder = "选择一个草稿后，这里会自动带入内容，供继续润色。",
  showAnnotations = true,
  sidePanel = null,
}: Props) {
  const [annotationNote, setAnnotationNote] = useState("");
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number; quote: string } | null>(null);

  const highlightedPreview = useMemo(() => {
    if (!annotations.length || !value) {
      return escapeHtml(value).replace(/\n/g, "<br />");
    }

    const sorted = [...annotations].sort((a, b) => a.start - b.start);
    let cursor = 0;
    let html = "";

    for (const annotation of sorted) {
      const start = Math.max(0, Math.min(annotation.start, value.length));
      const end = Math.max(start, Math.min(annotation.end, value.length));
      html += escapeHtml(value.slice(cursor, start)).replace(/\n/g, "<br />");
      html += `<mark class="rounded bg-[rgba(79,110,140,0.22)] px-1">${escapeHtml(value.slice(start, end))}</mark>`;
      cursor = end;
    }

    html += escapeHtml(value.slice(cursor)).replace(/\n/g, "<br />");
    return html;
  }, [annotations, value]);

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
    <section className="rounded-[28px] border border-line bg-white/78 p-6 shadow-soft">
      <div className="mb-4">
        <p className="text-sm uppercase tracking-[0.22em] text-amber">{eyebrow}</p>
        <h2 className="mt-2 font-serif text-3xl text-ink">{title}</h2>
        <p className="mt-2 text-sm leading-7 text-ink/66">
          在保留当前风格标签的前提下，把草稿修成能直接发送的最终版本。你也可以直接在 AI 回复里划词做高亮批注，再基于这些批注出新版本。
        </p>
      </div>

      <div
        className={`grid gap-4 ${
          sidePanel ? "xl:grid-cols-[minmax(0,1fr)_340px] 2xl:grid-cols-[minmax(0,1fr)_380px]" : ""
        }`}
      >
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onSelect={handleSelection}
          placeholder={placeholder}
          className="min-h-[360px] w-full rounded-[28px] border border-transparent bg-paper/72 px-5 py-5 text-[15px] leading-8 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)]"
        />
        {sidePanel ? <div className="xl:sticky xl:top-6 xl:self-start">{sidePanel}</div> : null}
      </div>

      {showAnnotations ? (
        <section className="mt-5 rounded-[26px] border border-line bg-paper/68 p-4">
          <div className="flex items-center gap-2">
            <Highlighter size={16} className="text-amber" />
            <p className="text-sm uppercase tracking-[0.2em] text-amber">AI 回复高亮批注</p>
          </div>
          <p className="mt-2 text-sm leading-7 text-ink/66">
            在当前 AI 回复中选中某一段文字后，可以记录“哪里不满意、哪里需要补充、哪里语气不对”。后续重生成会基于这些被标记的回复片段调整版本。
          </p>

          {selectionRange ? (
            <div className="mt-4 rounded-[22px] border border-amber/35 bg-white/82 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-ink/42">当前选中回复片段</p>
              <p className="mt-2 rounded-2xl bg-paper/85 px-3 py-3 text-sm leading-7 text-ink">{selectionRange.quote}</p>
              <textarea
                value={annotationNote}
                onChange={(event) => setAnnotationNote(event.target.value)}
                placeholder="例如：这句太空泛、这里需要更温柔、这里要补一个更具体的建议。"
                className="mt-3 min-h-[100px] w-full rounded-2xl border border-transparent bg-paper/72 px-4 py-4 text-sm leading-7 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.12)]"
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

          <details className="mt-4 rounded-[22px] border border-line bg-white/82 p-4">
            <summary className="cursor-pointer list-none">
              <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                <p className="text-xs uppercase tracking-[0.16em] text-ink/42">高亮预览</p>
                <p className="text-xs text-ink/50">
                  {annotations.length > 0 ? `${annotations.length} 条批注，点击展开查看` : "暂无批注"}
                </p>
              </div>
            </summary>
            <div
              className="mt-3 whitespace-pre-wrap text-sm leading-8 text-ink"
              dangerouslySetInnerHTML={{ __html: highlightedPreview || "暂无高亮批注。" }}
            />
          </details>

          {annotations.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {annotations.map((annotation, index) => (
                <div key={annotation.id} className="rounded-[22px] border border-line bg-white/82 p-4">
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
        </section>
      ) : null}
    </section>
  );
}
