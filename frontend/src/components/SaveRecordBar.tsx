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
    <div className="flex flex-wrap items-center justify-end gap-2">
        {batchMode && onExportReviewedBatch ? (
          <button
            type="button"
            disabled={!allCompleted || exportingReviewedBatch}
            onClick={onExportReviewedBatch}
            className="rounded-full border border-line bg-white/72 px-4 py-2 text-sm text-ink transition hover:bg-paper/85 disabled:cursor-not-allowed disabled:opacity-45"
          >
            {exportingReviewedBatch ? "导出中..." : "导出最终结果 Excel"}
          </button>
        ) : null}
        <button
          type="button"
          disabled={!canSave || isSaving}
          onClick={onSave}
          className="lilac-gradient rounded-full px-5 py-2.5 text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45"
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
  );
}
