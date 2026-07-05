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
  const historyEntries: HistoryEntry[] = [
    ...tasks.map((task) => ({ kind: "task" as const, task })),
    ...batchSessions.map((session) => ({
      kind: "batch" as const,
      session,
      mode: isMailBatchSession(session) ? ("mail_batch" as const) : ("excel_batch" as const),
    })),
  ].sort((a, b) => new Date(entryTime(b)).getTime() - new Date(entryTime(a)).getTime());

  const groups = historyEntries.reduce<Record<string, HistoryEntry[]>>((accumulator, entry) => {
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
      <div className="border-b border-line/70 bg-paper/62 p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <img src={logoSrc} alt="心灵笔友" className="h-10 w-12 shrink-0 object-contain mix-blend-multiply" />
            <div className="min-w-0">
              <h2 className="truncate font-serif text-lg text-ink">心灵笔友</h2>
              <p className="truncate text-xs text-ink/52">{counselorLabel}</p>
            </div>
          </div>
          <button type="button" onClick={onToggleCollapsed} className="rounded-full border border-line bg-white/76 p-2 text-ink">
            <PanelLeftClose size={16} />
          </button>
        </div>

        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={onNewSingle}
            className="flex min-w-0 flex-1 items-center justify-center gap-2 rounded-full bg-amber px-3 py-2 text-sm font-medium text-white"
          >
            <Plus size={16} />
            新建
          </button>
          <label
            title="上传 Excel 批量任务"
            className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-full border border-line bg-white/76 text-ink transition hover:bg-white"
          >
            <Upload size={16} />
            <span className="sr-only">{importingExcel ? "上传中" : "上传 Excel 批量任务"}</span>
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
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        <section className="mb-4 rounded-[18px] border border-line bg-white/72 shadow-[0_10px_28px_rgba(55,63,78,0.06)]">
          <button
            type="button"
            onClick={() => setPendingOpen((current) => !current)}
            className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left"
          >
            <span className="inline-flex items-center gap-2 text-sm font-medium text-ink">
              <Inbox size={16} />
              人工指派任务
              <span className="rounded-full bg-amber px-2 py-0.5 text-xs text-white">{assignedThreads.length}</span>
            </span>
            {pendingOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {pendingOpen ? (
            <div className="border-t border-line/70 p-2">
              <button
                type="button"
                onClick={onLoadAssignedQueue}
                disabled={loadingAssigned}
                className="mb-2 w-full rounded-full border border-line bg-paper/72 px-3 py-1.5 text-xs text-ink transition disabled:opacity-50"
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
                      className="rounded-[14px] border border-line bg-white/70 px-3 py-2 text-left transition hover:border-amber/50 hover:bg-paper/72"
                    >
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <span className="inline-flex min-w-0 items-center gap-1 text-xs text-ink/58">
                          <Mail size={13} />
                          <span className="truncate">{thread.signature || thread.user_id}</span>
                        </span>
                        <span className="rounded-full bg-mist px-2 py-0.5 text-[11px] text-ink/62">待回复</span>
                      </div>
                      <p className="truncate text-sm leading-5 text-ink">{latestUserMessage(thread)}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="px-2 py-3 text-xs leading-5 text-ink/52">暂无分配给你的待回复书信。</p>
              )}
            </div>
          ) : null}
        </section>

        <section>
          <p className="mb-1 px-2 text-[11px] uppercase tracking-[0.16em] text-ink/34">历史记录与批量任务</p>
          {["今天", "昨天", "过去 7 天", "更早"].map((label) =>
            groups[label]?.length ? (
              <div key={label} className="mb-3">
                <p className="mb-1 px-2 text-[11px] text-ink/32">{label}</p>
                <div className="grid gap-0.5">
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
                        className={`flex w-full items-center gap-2 rounded-[10px] px-2 py-2 text-left transition ${
                          active ? "bg-peach/28 text-ink" : "text-ink/72 hover:bg-paper/72"
                        }`}
                      >
                        {Icon ? <Icon size={14} className="shrink-0 text-ink/42" /> : <span className="w-3.5 shrink-0" />}
                        <span className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass(status)}`} title={statusLabel(status)} />
                        <span className="min-w-0 flex-1 truncate text-sm">
                          <span className={active ? "font-medium" : ""}>{entryTitle(entry)}</span>
                          <span className="text-ink/36"> · {statusLabel(status)}</span>
                          <span className="text-ink/36"> · {entrySummary(entry)}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null,
          )}
        </section>
      </div>
      <div className="border-t border-line/80 bg-white/72 p-3">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-[18px] px-3 py-2 text-left transition hover:bg-paper/75"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-mist text-sm font-medium text-ink">
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
