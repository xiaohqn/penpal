/**
 * 输入：
 * - 普通人格记录和安全回复记录的列表与详情查询结果。
 * - 用户在历史页里切换记录类型、选择某条记录，以及删除或导出安全回复记录的操作。
 * 输出：
 * - 渲染一个可在两类样本库之间切换的历史记录页面，并在安全样本库中提供删除与导出能力。
 * 作用：
 * - 统一承载普通人格回信样本库与安全回复样本库的浏览入口。
 */
import { Link } from "react-router-dom";
import { useState } from "react";

import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { RecordDetailDrawer } from "../components/RecordDetailDrawer";
import { RecordTable } from "../components/RecordTable";
import { SafetyRecordDetailDrawer } from "../components/SafetyRecordDetailDrawer";
import { useExportRecordsExcel, useRecord, useRecords } from "../features/records/hooks";
import {
  useDeleteSafetyRecord,
  useExportSafetyRecordsExcel,
  useSafetyRecord,
  useSafetyRecords,
} from "../features/safety-records/hooks";

export function RecordsPage() {
  const [recordKind, setRecordKind] = useState<"persona" | "safety">("persona");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [actionStatusText, setActionStatusText] = useState<string | null>(null);
  const recordsQuery = useRecords();
  const safetyRecordsQuery = useSafetyRecords();
  const recordQuery = useRecord(recordKind === "persona" ? selectedId : null);
  const safetyRecordQuery = useSafetyRecord(recordKind === "safety" ? selectedId : null);
  const deleteSafetyRecord = useDeleteSafetyRecord();
  const exportRecords = useExportRecordsExcel();
  const exportSafetyRecords = useExportSafetyRecordsExcel();
  const personaItems = recordsQuery.data?.items ?? [];
  const safetyItems = safetyRecordsQuery.data?.items ?? [];
  const activeItems = recordKind === "persona" ? personaItems : safetyItems;
  const activeListLoading = recordKind === "persona" ? recordsQuery.isLoading : safetyRecordsQuery.isLoading;

  async function handleExport() {
    const blob =
      recordKind === "persona"
        ? await exportRecords.mutateAsync()
        : await exportSafetyRecords.mutateAsync();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download =
      recordKind === "persona" ? "consultation_records.xlsx" : "safety_reply_records.xlsx";
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  async function handleDeleteSafetyRecord(recordId: number) {
    const confirmed = window.confirm("确认删除这条安全回复记录吗？删除后将无法恢复。");
    if (!confirmed) {
      return;
    }

    setActionStatusText(null);
    try {
      await deleteSafetyRecord.mutateAsync(recordId);
      if (recordKind === "safety" && selectedId === recordId) {
        setSelectedId(null);
      }
      setActionStatusText(`安全回复记录 #${recordId} 已删除。`);
    } catch (error) {
      setActionStatusText(error instanceof Error ? error.message : "安全回复记录删除失败");
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-8 xl:px-10">
      <div className="mx-auto max-w-[1500px]">
        <header className="mb-6 rounded-panel border border-line bg-white/75 p-6 shadow-soft backdrop-blur">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.28em] text-moss">History</p>
              <h1 className="mt-2 font-serif text-4xl text-ink">专家润色记录库</h1>
              <p className="mt-3 text-sm leading-7 text-ink/72">
                这里同时沉淀普通人格回信样本与安全回复样本，方便后续 few-shot / RAG 复用。
              </p>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleExport}
                disabled={exportRecords.isPending || exportSafetyRecords.isPending}
                className="rounded-full bg-ink px-5 py-3 text-sm text-paper transition disabled:cursor-not-allowed disabled:bg-ink/35"
              >
                {exportRecords.isPending || exportSafetyRecords.isPending
                  ? "导出中..."
                  : recordKind === "persona"
                    ? "导出记录 Excel"
                    : "导出安全回复 Excel"}
              </button>
              <Link
                to="/"
                className="rounded-full border border-line bg-paper/65 px-5 py-3 text-sm text-ink"
              >
                返回工作台
              </Link>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                setRecordKind("persona");
                setSelectedId(null);
                setActionStatusText(null);
              }}
              className={`rounded-full px-5 py-3 text-sm transition ${
                recordKind === "persona"
                  ? "bg-ink text-paper"
                  : "border border-line bg-paper/65 text-ink"
              }`}
            >
              人格回信记录
            </button>
            <button
              type="button"
              onClick={() => {
                setRecordKind("safety");
                setSelectedId(null);
                setActionStatusText(null);
              }}
              className={`rounded-full px-5 py-3 text-sm transition ${
                recordKind === "safety"
                  ? "bg-ink text-paper"
                  : "border border-line bg-paper/65 text-ink"
              }`}
            >
              安全回复记录
            </button>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section>
            {activeListLoading ? (
              <LoadingSkeleton />
            ) : (
              <RecordTable
                items={activeItems}
                selectedId={selectedId}
                onSelect={setSelectedId}
                renderActions={
                  recordKind === "safety"
                    ? (item) => {
                        const isDeleting =
                          deleteSafetyRecord.isPending && deleteSafetyRecord.variables === item.id;

                        return (
                          <button
                            type="button"
                            onClick={() => void handleDeleteSafetyRecord(item.id)}
                            disabled={isDeleting}
                            className="rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {isDeleting ? "删除中..." : "删除"}
                          </button>
                        );
                      }
                    : undefined
                }
              />
            )}
            {recordKind === "safety" && actionStatusText ? (
              <p className="mt-3 text-sm text-moss">{actionStatusText}</p>
            ) : null}
          </section>
          <section>
            {recordKind === "persona" ? (
              <RecordDetailDrawer record={recordQuery.data} />
            ) : (
              <SafetyRecordDetailDrawer record={safetyRecordQuery.data} />
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
