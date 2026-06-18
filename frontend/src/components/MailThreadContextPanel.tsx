import { AlertTriangle, History, Sparkles } from "lucide-react";

import type { MailThreadWorkspaceContext } from "../features/records/types";

type Props = {
  context?: MailThreadWorkspaceContext | Record<string, unknown> | null;
};

function isMailThreadContext(value: Props["context"]): value is MailThreadWorkspaceContext {
  return Boolean(value && typeof value === "object" && (value as MailThreadWorkspaceContext).kind === "mail_thread_reply");
}

function riskTone(level?: string) {
  if (level === "CRISIS" || level === "HIGH") return "border-red-200 bg-red-50 text-red-950";
  if (level === "MEDIUM") return "border-orange-200 bg-orange-50 text-orange-950";
  return "border-line bg-white/74 text-ink/72";
}

function uniqueRiskLines(signals?: string[], reasoning?: string) {
  const lines = [...(signals ?? []), reasoning ?? ""]
    .map((line) => line.trim())
    .filter(Boolean);
  return Array.from(new Set(lines));
}

export function MailThreadContextPanel({ context }: Props) {
  if (!isMailThreadContext(context)) return null;
  const risk = context.risk ?? {};
  const hasRisk = risk.level && risk.level !== "NONE";
  const transcript = context.transcript ?? [];
  const riskLines = uniqueRiskLines(risk.signals, risk.reasoning);

  return (
    <section className="rounded-panel border border-line bg-white/86 p-5 shadow-soft backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-amber">
            Assistant Context
          </div>
          <h2 className="mt-3 font-serif text-2xl text-ink">辅助上下文</h2>
        </div>
        <span className="rounded-full bg-paper px-3 py-1 text-xs text-ink/58">
          不属于用户原文
        </span>
      </div>

      <div className="mt-5 grid gap-4">
        <div className="rounded-[18px] border border-line bg-[#F8F6FF] p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Sparkles size={16} className="text-amber" />
            回应设置
          </p>
          <div className="mt-3 grid gap-2 text-sm leading-7 text-ink/68">
            <p>用户署名：{context.signature || "匿名"}</p>
            <p>回应偏好：{context.response_preference || "温柔陪伴"}</p>
          </div>
        </div>

        {hasRisk ? (
          <div className={`rounded-[18px] border p-4 ${riskTone(risk.level)}`}>
            <p className="flex items-center gap-2 text-sm font-semibold">
              <AlertTriangle size={16} />
              风险提示：{risk.level}
            </p>
            <div className="mt-3 grid gap-1 text-sm leading-7">
              {riskLines.slice(0, 5).map((signal) => (
                <p key={signal}>• {signal}</p>
              ))}
            </div>
          </div>
        ) : null}

        {transcript.length > 0 ? (
          <div className="rounded-[18px] border border-line bg-white/72 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-ink">
              <History size={16} className="text-amber" />
              完整书信往返
            </p>
            <div className="mt-3 grid gap-3">
              {transcript.map((message, index) => (
                <div key={message.id ?? index} className="rounded-[14px] bg-paper/70 px-4 py-3">
                  <p className="text-xs font-semibold text-amber">{message.label || "书信"}</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-ink/68">
                    {message.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
