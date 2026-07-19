import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { exportResearchEvents } from "../features/records/api";

import { useAuth } from "../app/auth";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { RecordDetailDrawer } from "../components/RecordDetailDrawer";
import { RecordTable } from "../components/RecordTable";
import scirScLogo from "../assets/logo-mark.png";
import { useExportRecordsExcel, useRecord, useRecords, useUpdateRecord } from "../features/records/hooks";
import type { UpdateRecordPayload } from "../features/records/types";

export function RecordsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const recordsQuery = useRecords(page, 20, scope);
  const recordQuery = useRecord(selectedId, scope);
  const exportRecords = useExportRecordsExcel();
  const [exportingEvents, setExportingEvents] = useState(false);

  async function handleExportEvents() {
    setExportingEvents(true);
    try {
      const blob = await exportResearchEvents(scope);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "research_events.xlsx";
      anchor.click();
      window.URL.revokeObjectURL(url);
    } finally {
      setExportingEvents(false);
    }
  }
  const updateRecord = useUpdateRecord();
  const total = recordsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  async function handleExport() {
    const blob = await exportRecords.mutateAsync(scope);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "consultation_records.xlsx";
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  async function handleUpdateRecord(recordId: number, payload: UpdateRecordPayload) {
    await updateRecord.mutateAsync({ recordId, payload, scope });
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-8 xl:px-10">
      <div className="mx-auto max-w-[1500px]">
        <header className="surface-glow mb-5 overflow-hidden rounded-[26px] border border-white/70 bg-white/84 px-5 py-4 shadow-soft backdrop-blur">
          <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-col gap-3 md:flex-row md:items-center">
              <img src={scirScLogo} alt="心灵笔友标志" className="h-20 w-28 shrink-0 object-contain mix-blend-multiply md:h-24 md:w-32" />
              <div className="min-w-0">
                <p className="rounded-full bg-mist/80 px-3 py-1 text-sm uppercase tracking-[0.28em] text-amber">
                  History
                </p>
                <h1 className="mt-2 font-serif text-3xl text-ink md:text-4xl">
                  <span className="lilac-text">专家润色记录库</span>
                </h1>
                <p className="mt-1 text-sm leading-6 text-ink/64">
                  {scope === "mine" ? `当前咨询师：${user?.counselorId ?? "default"}` : "正在查看全部咨询师记录"}
                </p>
              </div>
            </div>
            <div className="relative flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-end">
              <div className="inline-flex rounded-full border border-line bg-paper/70 p-1">
                <button
                  type="button"
                  onClick={() => {
                    setScope("mine");
                    setPage(1);
                    setSelectedId(null);
                  }}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    scope === "mine" ? "lilac-gradient text-white shadow-card" : "text-ink/72"
                  }`}
                >
                  我的记录
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setScope("all");
                    setPage(1);
                    setSelectedId(null);
                  }}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    scope === "all" ? "lilac-gradient text-white shadow-card" : "text-ink/72"
                  }`}
                >
                  全部记录
                </button>
              </div>
              <button
                type="button"
                onClick={handleExport}
                disabled={exportRecords.isPending}
                className="lilac-gradient rounded-full px-5 py-3 text-sm font-medium text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-45"
              >
                {exportRecords.isPending ? "导出中..." : "导出记录 Excel"}
              </button>
              <button
                type="button"
                onClick={handleExportEvents}
                disabled={exportingEvents}
                className="rounded-full border border-amber bg-white/75 px-5 py-3 text-sm font-medium text-amber transition disabled:opacity-45"
              >
                {exportingEvents ? "导出中..." : "导出研究轨迹 Excel"}
              </button>
              <Link
                to="/"
                className="rounded-full border border-line bg-paper/65 px-5 py-3 text-sm text-ink"
              >
                返回工作台
              </Link>
              <button
                type="button"
                onClick={() => {
                  logout();
                  navigate("/login", { replace: true });
                }}
                className="rounded-full border border-line bg-paper/65 px-5 py-3 text-sm text-ink"
              >
                退出登录
              </button>
            </div>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(520px,0.82fr)_minmax(620px,1.18fr)]">
          <section className="min-w-0">
            {recordsQuery.isLoading ? (
              <LoadingSkeleton />
            ) : (
              <div className="grid gap-3">
                <div className="flex flex-col gap-3 rounded-[20px] border border-line bg-white/72 px-4 py-3 text-sm text-ink/68 shadow-card sm:flex-row sm:items-center sm:justify-between">
                  <span>
                    共 {total} 条记录，当前第 {page} / {totalPages} 页
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={page <= 1 || recordsQuery.isFetching}
                      onClick={() => {
                        setPage((current) => Math.max(1, current - 1));
                        setSelectedId(null);
                      }}
                      className="rounded-full border border-line bg-paper/70 px-4 py-2 text-sm text-ink transition disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      上一页
                    </button>
                    <button
                      type="button"
                      disabled={page >= totalPages || recordsQuery.isFetching}
                      onClick={() => {
                        setPage((current) => Math.min(totalPages, current + 1));
                        setSelectedId(null);
                      }}
                      className="rounded-full border border-line bg-paper/70 px-4 py-2 text-sm text-ink transition disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      下一页
                    </button>
                  </div>
                </div>
                <RecordTable
                  items={recordsQuery.data?.items ?? []}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
              </div>
            )}
          </section>
          <section className="min-w-0">
            <RecordDetailDrawer
              record={recordQuery.data}
              onSave={handleUpdateRecord}
              saving={updateRecord.isPending}
            />
          </section>
        </div>
      </div>
    </main>
  );
}
