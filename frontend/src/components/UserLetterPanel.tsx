import type { ReactNode } from "react";

/**
 * 输入：
 * - value / onChange：原始来信正文及其回写函数。
 * - readOnly：批量模式等场景下是否禁止编辑来信。
 * - batchMeta：批量处理时展示当前条目位置的辅助信息。
 * - headerAside：可选的头部右侧操作区，通常用于放置与当前来信强相关的快捷操作，例如安全检测入口。
 * 输出：
 * - 渲染原始来信输入面板，并在需要时把关联操作固定在面板头部右侧。
 * 作用：
 * - 这个组件负责承载用户原始输入，同时给页面保留一个稳定的头部扩展位，
 *   让“与来信强相关”的操作不必再额外占据下方滚动空间；当扩展位放的是紧凑安全检测入口时，
 *   这里也会自动按内容宽度收窄；安全检测入口本身会通过右对齐反馈文字，
 *   避免提示信息贴到标题区域。
 */
type Props = {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  headerAside?: ReactNode;
  batchMeta?: {
    current: number;
    total: number;
    rowNumber: number;
  } | null;
};

export function UserLetterPanel({
  value,
  onChange,
  readOnly = false,
  headerAside = null,
  batchMeta,
}: Props) {
  return (
    <section className="rounded-panel border border-line bg-white/80 p-6 shadow-soft backdrop-blur xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
                Context
              </div>
              <h2 className="mt-3 whitespace-nowrap font-serif text-3xl text-ink">原始来信</h2>
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
        </div>
        {headerAside ? (
          <div className="flex items-start xl:flex-none">
            {headerAside}
          </div>
        ) : null}
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="输入来信内容，支持较长文本。"
        readOnly={readOnly}
        className="mt-5 min-h-[280px] w-full rounded-[28px] border border-transparent bg-paper/75 px-5 py-5 text-[15px] leading-8 text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(79,110,140,0.14)] xl:min-h-[calc(100vh-25rem)]"
      />
    </section>
  );
}
