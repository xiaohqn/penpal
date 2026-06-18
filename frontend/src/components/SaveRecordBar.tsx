type Props = {
  canSave: boolean;
  isSaving: boolean;
  onSave: () => void;
  batchMode?: boolean;
  allCompleted?: boolean;
  isLastBatchItem?: boolean;
  onExportReviewedBatch?: (() => void) | null;
  exportingReviewedBatch?: boolean;
};

export function SaveRecordBar({
  canSave,
  isSaving,
  onSave,
  batchMode = false,
  allCompleted = false,
  isLastBatchItem = false,
  onExportReviewedBatch = null,
  exportingReviewedBatch = false,
}: Props) {
  return (
    <div className="lilac-gradient flex flex-col gap-4 rounded-panel border border-white/30 p-5 text-white shadow-[0_24px_60px_rgba(108,83,171,0.26)] md:flex-row md:items-center md:justify-between">
      <div className="max-w-2xl">
        <p className="text-xs uppercase tracking-[0.18em] text-white/60">最后一步</p>
        <p className="mt-2 text-sm leading-7 text-white/82">
          {batchMode && allCompleted
            ? "当前批次已经全部完成，可以回看版本、继续修改已完成条目，或导出最终结果。"
            : batchMode && isLastBatchItem
              ? "这是当前批次的最后一条。完成后会停留在当前任务，并显示全部完成状态。"
            : batchMode
              ? "当前条目完成后会进入下一条；只要留下专家批注或回复高亮批注，系统就会自动记录处理过程和最终版本。"
            : "保存后会把原始问题、候选草稿、处理过程、批注和最终满意版本一起入库。"}
        </p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        {batchMode && onExportReviewedBatch ? (
          <button
            type="button"
            disabled={!allCompleted || exportingReviewedBatch}
            onClick={onExportReviewedBatch}
            className="rounded-full border border-white/18 bg-white/8 px-5 py-3 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-45"
          >
            {exportingReviewedBatch ? "导出中..." : "导出最终结果 Excel"}
          </button>
        ) : null}
        <button
          type="button"
          disabled={!canSave || isSaving}
          onClick={onSave}
          className="rounded-full bg-white px-5 py-3 text-sm font-medium text-ink shadow-card transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-white/40 disabled:text-ink/55"
        >
          {isSaving
            ? "保存中..."
            : batchMode && allCompleted
              ? "已全部完成"
              : batchMode && isLastBatchItem
                ? "完成当前条目"
                : batchMode
                  ? "完成当前条目并进入下一条"
                  : "记录处理过程与满意版本"}
        </button>
      </div>
    </div>
  );
}
