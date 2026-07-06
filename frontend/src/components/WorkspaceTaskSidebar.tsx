import { ChevronDown, ChevronUp, FileSpreadsheet, Inbox, LogOut, Mail, PanelLeftClose, PenLine, Plus, Sparkles, Upload } from "lucide-react";
import { useState } from "react";

import type { MailThread } from "../features/mailThreads/types";
import type { BatchSessionListItem } from "../features/records/types";
import type { WorkspaceTask } from "../features/workspaceTasks/types";

type HistoryEntry =
  | { kind: "task"; task: WorkspaceTask }
  | { kind: "batch"; session: BatchSessionListItem; mode: "excel_batch" | "mail_batch" };

type Props = {
  tasks: WorkspaceTask[];
  batchSessions: BatchSessionListItem[];
  assignedThreads: MailThread[];
  activeTaskId: number | null;
  activeBatchSessionId: number | null;
  collapsed: boolean;
  importingExcel: boolean;
  loadingAssigned: boolean;
  logoSrc: string;
  counselorLabel: string;
  onToggleCollapsed: () => void;
  onLogout: () => void;
  onNewSingle: () => void;
  onUploadExcel: (file: File) => void;
  onSelectTask: (task: WorkspaceTask) => void;
  onSelectBatch: (session: BatchSessionListItem, mode: "excel_batch" | "mail_batch") => void;
  onSelectAssignedThread: (thread: MailThread) => void;
  onLoadAssignedQueue: () => void;
};

function isMailBatchSession(session: BatchSessionListItem) {
  return session.title.includes("人工书信") || session.source_file_name.includes("人工书信");
}

function groupLabel(value: string) {
  const date = new Date(value);
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startValue = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const diffDays = Math.round((startToday - startValue) / 86400000);
  if (diffDays <= 0) return "今天";
  if (diffDays === 1) return "昨天";
  if (diffDays <= 7) return "过去 7 天";
  return "更早";
}

function statusLabel(status: string) {
  if (status === "completed") return "已完成";
  if (status === "in_progress") return "处理中";
  if (status === "processing") return "处理中";
  return "草稿";
}

function statusDotClass(status: string) {
  if (status === "completed") return "bg-moss";
  if (status === "in_progress" || status === "processing") return "bg-amber";
  return "bg-ink/22";
}

function entryTime(entry: HistoryEntry) {
  return entry.kind === "task" ? entry.task.updated_at : entry.session.updated_at;
}

function entryTitle(entry: HistoryEntry) {
  if (entry.kind === "task") {
    return entry.task.title || entry.task.summary || "单封 AI 工单";
  }
  return entry.session.source_file_name || entry.session.title || "批量任务";
}

function entrySummary(entry: HistoryEntry) {
  if (entry.kind === "task") {
    return entry.task.summary || entry.task.state_json?.userInput || "暂无摘要";
  }
  return `${entry.session.completed_items}/${entry.session.total_items} 完成`;
}

function latestUserMessage(thread: MailThread) {
  const message = [...thread.messages].reverse().find((item) => item.sender_type === "user");
  return message?.content || thread.title || "待回复书信";
}

export function WorkspaceTaskSidebar({
  tasks,
  batchSessions,
  assignedThreads,
  activeTaskId,
  activeBatchSessionId,
  collapsed,
  importingExcel,
  loadingAssigned,
  logoSrc,
  counselorLabel,
  onToggleCollapsed,
  onLogout,
  onNewSingle,
  onUploadExcel,
  onSelectTask,
  onSelectBatch,
  onSelectAssignedThread,
  onLoadAssignedQueue,
}: Props) {
  const [pendingOpen, setPendingOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<"single" | "batch">("single");
  const historyEntries: HistoryEntry[] = [
    ...tasks.map((task) => ({ kind: "task" as const, task })),
    ...batchSessions.map((session) => ({
      kind: "batch" as const,
      session,
      mode: isMailBatchSession(session) ? ("mail_batch" as const) : ("excel_batch" as const),
    })),
  ].sort((a, b) => new Date(entryTime(b)).getTime() - new Date(entryTime(a)).getTime());
  const visibleHistoryEntries = historyEntries.filter((entry) => {
    if (activeTab === "batch") {
      return entry.kind === "batch" && entry.mode === "excel_batch";
    }
    return entry.kind === "task" || (entry.kind === "batch" && entry.mode === "mail_batch");
  });

  const groups = visibleHistoryEntries.reduce<Record<string, HistoryEntry[]>>((accumulator, entry) => {
    const label = groupLabel(entryTime(entry));
    accumulator[label] = [...(accumulator[label] ?? []), entry];
    return accumulator;
  }, {});

  if (collapsed) {
    return (
      <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-14 shrink-0 flex-col items-center gap-3 rounded-[22px] border border-line bg-white/82 p-2 shadow-card xl:flex">
        <img src={logoSrc} alt="心灵笔友" className="h-8 w-8 object-contain mix-blend-multiply" />
        <button type="button" onClick={onToggleCollapsed} className="rounded-full border border-line bg-paper/70 p-2 text-ink">
          <PenLine size={17} />
        </button>
        <button type="button" onClick={onNewSingle} className="rounded-full bg-amber p-2 text-white">
          <Plus size={17} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-[300px] shrink-0 flex-col overflow-hidden rounded-[24px] border border-line bg-white/84 shadow-card xl:flex">
      <div className="max-w-full overflow-hidden border-b border-line/70 bg-paper/62 px-3 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
            <img src={logoSrc} alt="心灵笔友" className="h-8 w-10 shrink-0 object-contain mix-blend-multiply" />
            <div className="min-w-0">
              <h2 className="truncate font-serif text-base text-ink">心灵笔友</h2>
              <p className="truncate text-xs text-ink/52">{counselorLabel}</p>
            </div>
          </div>
          <button type="button" onClick={onToggleCollapsed} className="rounded-full border border-line bg-white/76 p-2 text-ink">
            <PanelLeftClose size={16} />
          </button>
        </div>

        <div className="mt-2">
          {activeTab === "single" ? (
            <button
              type="button"
              onClick={onNewSingle}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-amber px-3 py-1.5 text-sm font-medium text-white"
            >
              <Plus size={16} />
              新建
            </button>
          ) : (
            <label
              title="上传 Excel 批量任务"
              className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-full bg-amber px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-92"
            >
              <Upload size={16} />
              {importingExcel ? "上传中" : "上传 Excel"}
              <input
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    onUploadExcel(file);
                    event.target.value = "";
                  }
                }}
              />
            </label>
          )}
          <div className="mt-2 grid grid-cols-2 rounded-full border border-line bg-white/62 p-1 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab("single")}
              className={`rounded-full px-2 py-1.5 transition ${activeTab === "single" ? "bg-white text-ink shadow-card" : "text-ink/48 hover:text-ink"}`}
            >
              单封信件
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("batch")}
              className={`rounded-full px-2 py-1.5 transition ${activeTab === "batch" ? "bg-white text-ink shadow-card" : "text-ink/48 hover:text-ink"}`}
            >
              批量任务
            </button>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {activeTab === "single" ? (
        <section className="mb-3 max-w-full overflow-hidden rounded-[16px] border border-line bg-white/72 shadow-[0_10px_28px_rgba(55,63,78,0.06)]">
          <button
            type="button"
            onClick={() => setPendingOpen((current) => !current)}
            className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left"
          >
            <span className="inline-flex items-center gap-2 text-[13px] font-medium text-ink">
              <Inbox size={15} />
              人工指派任务
              <span className="rounded-full bg-amber px-2 py-0.5 text-xs text-white">{assignedThreads.length}</span>
            </span>
            {pendingOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {pendingOpen ? (
            <div className="border-t border-line/70 p-1.5">
              <button
                type="button"
                onClick={onLoadAssignedQueue}
                disabled={loadingAssigned}
                className="mb-1.5 w-full rounded-full border border-line bg-paper/72 px-3 py-1 text-xs text-ink transition disabled:opacity-50"
              >
                {loadingAssigned ? "载入中..." : "载入全部待办"}
              </button>
              {assignedThreads.length > 0 ? (
                <div className="grid gap-2">
                  {assignedThreads.map((thread) => (
                    <button
                      key={thread.id}
                      type="button"
                      onClick={() => onSelectAssignedThread(thread)}
                      className="w-full max-w-full overflow-hidden rounded-[13px] border border-line bg-white/70 px-2.5 py-1.5 text-left transition hover:border-amber/50 hover:bg-paper/72"
                    >
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <span className="inline-flex min-w-0 flex-1 items-center gap-1 overflow-hidden text-[11px] text-ink/58">
                          <Mail size={13} />
                          <span className="truncate">{thread.signature || thread.user_id}</span>
                        </span>
                        <span className="rounded-full bg-mist px-2 py-0.5 text-[11px] text-ink/62">待回复</span>
                      </div>
                      <p className="truncate text-[13px] leading-5 text-ink">{latestUserMessage(thread)}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="px-2 py-3 text-xs leading-5 text-ink/52">暂无分配给你的待回复书信。</p>
              )}
            </div>
          ) : null}
        </section>
        ) : null}

        <section>
          <p className="mb-1.5 px-2 text-xs font-medium text-ink/48">
            {activeTab === "single" ? "单封历史" : "Excel 批量任务"}
          </p>
          {["今天", "昨天", "过去 7 天", "更早"].map((label) =>
            groups[label]?.length ? (
              <div key={label} className="mb-2.5">
                <p className="mb-1 px-2 text-[11px] text-ink/38">{label}</p>
                <div className="grid gap-1.5">
                  {groups[label].map((entry) => {
                    const active =
                      entry.kind === "task"
                        ? activeTaskId === entry.task.id
                        : activeBatchSessionId === entry.session.id;
                    const Icon = entry.kind === "batch" ? (entry.mode === "mail_batch" ? Mail : FileSpreadsheet) : null;
                    const status = entry.kind === "task" ? entry.task.status : entry.session.status;
                    return (
                      <button
                        key={entry.kind === "task" ? `task-${entry.task.id}` : `batch-${entry.session.id}`}
                        type="button"
                        onClick={() =>
                          entry.kind === "task" ? onSelectTask(entry.task) : onSelectBatch(entry.session, entry.mode)
                        }
                        className={`w-full max-w-full overflow-hidden rounded-[14px] border px-2 py-2 text-left transition ${
                          active ? "border-amber bg-peach/22 shadow-card" : "border-line bg-white/66 hover:bg-paper/72"
                        }`}
                      >
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="inline-flex min-w-0 flex-1 items-center gap-1.5 overflow-hidden text-[11px] text-ink/58">
                            {Icon ? <Icon size={14} className="shrink-0" /> : null}
                            <span className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass(status)}`} />
                            <span className="truncate">
                              {entry.kind === "batch" ? (entry.mode === "mail_batch" ? "批量/人工" : "批量/Excel") : "单封"}
                            </span>
                          </span>
                          <span className="shrink-0 rounded-full bg-mist px-1.5 py-0.5 text-[10px] text-ink/60">{statusLabel(status)}</span>
                        </div>
                        <p className="truncate text-[13px] font-medium leading-5 text-ink">{entryTitle(entry)}</p>
                        <p className="mt-0.5 truncate text-[11px] leading-4 text-ink/52">{entrySummary(entry)}</p>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null,
          )}
        </section>
      </div>
      <div className="border-t border-line/80 bg-white/72 p-2.5">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-2 rounded-[16px] px-2.5 py-1.5 text-left transition hover:bg-paper/75"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mist text-sm font-medium text-ink">
            {counselorLabel.slice(0, 1).toUpperCase()}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm text-ink">{counselorLabel}</span>
            <span className="block text-xs text-ink/48">退出登录</span>
          </span>
          <LogOut size={15} className="text-ink/48" />
        </button>
      </div>
    </aside>
  );
}
