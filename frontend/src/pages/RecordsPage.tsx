import { Link } from "react-router-dom";
import { useState } from "react";

import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { RecordDetailDrawer } from "../components/RecordDetailDrawer";
import { RecordTable } from "../components/RecordTable";
import { useExportRecordsExcel, useRecord, useRecords } from "../features/records/hooks";

export function RecordsPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const recordsQuery = useRecords();
  const recordQuery = useRecord(selectedId);
  const exportRecords = useExportRecordsExcel();

  async function handleExport() {
    const blob = await exportRecords.mutateAsync();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "consultation_records.xlsx";
    anchor.click();
    window.URL.revokeObjectURL(url);
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
                这里沉淀的是未来最有价值的 few-shot / RAG 语料。
              </p>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleExport}
                disabled={exportRecords.isPending}
                className="rounded-full bg-ink px-5 py-3 text-sm text-paper transition disabled:cursor-not-allowed disabled:bg-ink/35"
              >
                {exportRecords.isPending ? "导出中..." : "导出记录 Excel"}
              </button>
              <Link
                to="/"
                className="rounded-full border border-line bg-paper/65 px-5 py-3 text-sm text-ink"
              >
                返回工作台
              </Link>
            </div>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section>
            {recordsQuery.isLoading ? (
              <LoadingSkeleton />
            ) : (
              <RecordTable
                items={recordsQuery.data?.items ?? []}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            )}
          </section>
          <section>
            <RecordDetailDrawer record={recordQuery.data} />
          </section>
        </div>
      </div>
    </main>
  );
}
