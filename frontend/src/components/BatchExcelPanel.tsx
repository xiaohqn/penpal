import { useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, ChevronsUpDown, FileSpreadsheet, Upload } from "lucide-react";

type BatchExcelItem = {
  row_number: number;
  user_input: string;
  selected_persona_names: string[];
};

type Props = {
  importing: boolean;
  fileName: string | null;
  items: BatchExcelItem[];
  completedCount: number;
  currentIndex: number;
  activeRowNumber: number | null;
  completedRowNumbers: number[];
  onImport: (file: File) => void;
  onSelectRow: (rowNumber: number) => void;
  onPrevious: () => void;
  onNext: () => void;
};

export function BatchExcelPanel({
  importing,
  fileName,
  items,
  completedCount,
  currentIndex,
  activeRowNumber,
  completedRowNumbers,
  onImport,
  onSelectRow,
  onPrevious,
  onNext,
}: Props) {
  const [expanded, setExpanded] = useState(true);
  const progress = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0;

  return (
    <aside className="rounded-panel border border-line bg-white/82 p-5 shadow-soft backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
            <FileSpreadsheet size={14} />
            Batch Drawer
          </div>
          <h2 className="mt-3 font-serif text-2xl text-ink">批量任务侧栏</h2>
          <p className="mt-2 text-sm leading-7 text-ink/66">
            Excel 只负责导入问题列表。每条来信的风格、润色和批注，都在主工作流里由专家自由决定。
          </p>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className="inline-flex shrink-0 items-center gap-2 rounded-full border border-line bg-white/72 px-3 py-2 text-sm text-ink/74 transition hover:bg-paper/80"
        >
          <ChevronsUpDown size={16} />
          {expanded ? "收起" : "展开"}
        </button>
      </div>

      <label className="mt-5 flex cursor-pointer items-center justify-center gap-2 rounded-[26px] border border-dashed border-line bg-paper/70 px-4 py-4 text-sm text-ink transition hover:border-amber/45 hover:bg-white">
        <Upload size={16} />
        {importing ? "导入中..." : "上传 Excel"}
        <input
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              onImport(file);
              event.target.value = "";
            }
          }}
        />
      </label>

      <div className="mt-4 rounded-[26px] border border-line bg-paper/72 p-4">
        <div className="flex items-center justify-between gap-3 text-sm text-ink/72">
          <span className="truncate">{fileName ? `当前文件：${fileName}` : "尚未上传文件"}</span>
          <span>{items.length} 条</span>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <div className="rounded-[22px] bg-white/72 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-ink/42">完成进度</p>
            <p className="mt-2 text-xl font-semibold text-ink">
              {completedCount} / {items.length || 0}
            </p>
          </div>
          <div className="rounded-[22px] bg-white/72 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-ink/42">当前处理</p>
            <p className="mt-2 text-xl font-semibold text-ink">
              {items.length > 0 ? `${currentIndex + 1} / ${items.length}` : "--"}
            </p>
          </div>
          <div className="rounded-[22px] bg-white/72 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-ink/42">完成率</p>
            <p className="mt-2 text-xl font-semibold text-ink">{progress}%</p>
          </div>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/72">
          <div className="h-full rounded-full bg-amber transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {expanded ? (
        <div className="mt-4">
          {items.length > 0 ? (
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onPrevious}
                disabled={currentIndex <= 0}
                className="inline-flex items-center gap-2 rounded-full border border-line bg-white/72 px-4 py-2 text-sm text-ink transition disabled:cursor-not-allowed disabled:opacity-45"
              >
                <ChevronLeft size={16} />
                上一条
              </button>
              <button
                type="button"
                onClick={onNext}
                disabled={currentIndex >= items.length - 1}
                className="inline-flex items-center gap-2 rounded-full border border-line bg-white/72 px-4 py-2 text-sm text-ink transition disabled:cursor-not-allowed disabled:opacity-45"
              >
                下一条
                <ChevronRight size={16} />
              </button>
            </div>
          ) : null}
          {items.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {items.map((item, index) => {
                const isActive = item.row_number === activeRowNumber;
                const isCompleted = completedRowNumbers.includes(item.row_number);
                return (
                  <button
                    key={item.row_number}
                    type="button"
                    onClick={() => onSelectRow(item.row_number)}
                    className={`flex w-full items-start justify-between gap-3 rounded-[24px] border px-4 py-4 text-left transition ${
                      isActive
                        ? "border-amber bg-[rgba(79,110,140,0.09)] shadow-card"
                        : "border-line bg-white/72 hover:border-amber/50 hover:bg-white"
                    }`}
                  >
                    <div>
                      <div className="text-sm font-medium text-ink">第 {index + 1} 条</div>
                      <div className="mt-2 text-sm leading-6 text-ink/65">{item.user_input.slice(0, 84)}...</div>
                    </div>
                    <span
                      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-1 text-xs ${
                        isActive
                          ? "bg-amber text-white"
                          : isCompleted
                            ? "bg-moss/24 text-ink"
                            : "bg-mist text-ink/70"
                      }`}
                    >
                      {isCompleted ? <CheckCircle2 size={14} /> : null}
                      {isActive ? "当前" : isCompleted ? "已完成" : "待处理"}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="mt-4 rounded-[24px] border border-dashed border-line bg-white/58 px-4 py-5 text-sm leading-7 text-ink/62">
              上传 Excel 后，这里会出现批量条目列表。你可以在右侧随时切换任务，在中间主流程里完成生成、润色和批注。
            </div>
          )}
        </div>
      ) : null}
    </aside>
  );
}
