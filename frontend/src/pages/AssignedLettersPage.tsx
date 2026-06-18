import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Inbox, Layers3, LogOut, Send, Wand2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../app/auth";
import scirScLogo from "../assets/logo-mark.png";
import { generateFromPlan } from "../features/generation/api";
import type { DraftCandidate, SafetyReview } from "../features/generation/types";
import {
  useAssignedMailThreads,
  useCreateAssignedThreadWorkspaceSession,
  useCreateAssignedThreadsWorkspaceSession,
  useSubmitCounselorThreadReply,
} from "../features/mailThreads/hooks";
import type { MailMessage, MailThread, RiskAssessment, RiskLevel } from "../features/mailThreads/types";

function isAnswered(thread: MailThread) {
  return thread.status === "waiting_user" || thread.status === "completed";
}

function latestUserMessage(thread: MailThread) {
  return [...thread.messages].reverse().find((message) => message.sender_type === "user") ?? null;
}

function latestUserRisk(thread: MailThread) {
  return [...thread.risk_assessments].reverse().find((assessment) => assessment.target_type === "user_letter") ?? null;
}

function riskRank(level: RiskLevel | string) {
  return { NONE: 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRISIS: 4 }[level as RiskLevel] ?? 0;
}

function threadRiskLevel(thread: MailThread) {
  return thread.risk_assessments
    .filter((assessment) => assessment.target_type === "user_letter")
    .reduce<RiskLevel>((level, assessment) => (riskRank(assessment.risk_level) > riskRank(level) ? assessment.risk_level : level), "NONE");
}

function formatRelativeTime(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(diff / 60000));
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  return `${Math.floor(hours / 24)}天前`;
}

function getPersonaForPreference(preference: string) {
  if (preference === "理性分析") return "理性破局教练";
  if (preference === "启发引导") return "启发故事导师";
  return "温暖倾听者";
}

function buildCounselorAssistPrompt(thread: MailThread) {
  const orderedMessages = [...thread.messages].sort(
    (first, second) =>
      new Date(first.created_at).getTime() - new Date(second.created_at).getTime() || first.id - second.id,
  );
  const transcript = orderedMessages
    .map((message) => {
      const role = message.sender_type === "user" ? "用户来信" : message.sender_type === "counselor" ? "咨询师既往回信" : "AI既往回信";
      return `${role}：\n${message.content}`;
    })
    .join("\n\n");
  const risk = latestUserRisk(thread);
  const memory = thread.memory?.summary ? `【系统记忆摘要】\n${thread.memory.summary}\n\n` : "";
  const riskBlock = risk
    ? `【风险提示】\n等级：${risk.risk_level}\n触发因素：${risk.signals.join("；") || "无"}\n\n`
    : "";
  return `${memory}${riskBlock}【回应偏好】${thread.response_preference || "温柔陪伴"}\n\n【完整书信往返】\n${transcript}\n\n请为咨询师起草一封可以修改后发送给用户的回信。要求：\n1. 保持书信口吻，温和、具体、不评判。\n2. 不要声称自己是 AI。\n3. 如果存在高风险或危机线索，优先做安全承接，提醒联系现实支持与紧急服务，避免给危险方法或轻率承诺。\n4. 不要替代医疗诊断或治疗。`;
}

export function AssignedLettersPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const threadsQuery = useAssignedMailThreads();
  const submitReply = useSubmitCounselorThreadReply();
  const createThreadWorkspace = useCreateAssignedThreadWorkspaceSession();
  const createThreadsWorkspace = useCreateAssignedThreadsWorkspaceSession();
  const rawItems = threadsQuery.data?.items ?? [];
  const taskNumbers = useMemo(() => {
    const chronologicalItems = [...rawItems].sort(
      (first, second) =>
        new Date(first.created_at).getTime() - new Date(second.created_at).getTime() || first.id - second.id,
    );
    return new Map(chronologicalItems.map((item, index) => [item.id, index + 1]));
  }, [rawItems]);
  const items = useMemo(
    () =>
      [...rawItems].sort((first, second) => {
        const firstAnswered = isAnswered(first);
        const secondAnswered = isAnswered(second);
        if (firstAnswered !== secondAnswered) {
          return firstAnswered ? 1 : -1;
        }
        const timeDifference = new Date(first.updated_at).getTime() - new Date(second.updated_at).getTime();
        return firstAnswered ? -timeDifference : timeDifference;
      }),
    [rawItems],
  );
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");
  const [message, setMessage] = useState("");
  const [assistLoading, setAssistLoading] = useState(false);
  const [assistDraft, setAssistDraft] = useState<DraftCandidate | null>(null);

  const selected = items.find((item) => item.id === selectedId) ?? items[0] ?? null;

  useEffect(() => {
    if (!selected) return;
    setSelectedId(selected.id);
    setReplyText("");
    setMessage("");
    setAssistDraft(null);
  }, [selected?.id]);

  async function handleSubmit() {
    if (!selected || !replyText.trim()) {
      setMessage("请先写下回复内容。");
      return;
    }
    try {
      await submitReply.mutateAsync({ threadId: selected.id, content: replyText.trim() });
      setReplyText("");
      setMessage("回信已送达用户信箱。");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "发送失败");
    }
  }

  async function handleAssistDraft() {
    if (!selected) return;
    setAssistLoading(true);
    setMessage("");
    try {
      const draft = await generateFromPlan({
        user_input: buildCounselorAssistPrompt(selected),
        persona_name: getPersonaForPreference(selected.response_preference),
        planner_output: {
          intention: "咨询师人工回信辅助起草",
          risk_assessment: latestUserRisk(selected)?.reasoning ?? "",
          response_focus: "基于完整书信上下文、风险提示和用户回应偏好，生成一封供咨询师审阅修改后发送的回信。",
          must_avoid: ["不要声称自己是 AI", "不要替代医疗诊断", "不要提供危险行为方法"],
        },
        source_mode: "api",
      });
      setAssistDraft(draft);
      setReplyText(draft.response);
      setMessage(draft.safety_review?.replacement_used ? "AI辅助草稿已通过安全替换，请务必人工复核后再发送。" : "AI辅助草稿已填入，请审阅修改后发送。");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "AI辅助起草失败");
    } finally {
      setAssistLoading(false);
    }
  }

  async function openThreadInWorkspace(thread: MailThread) {
    setMessage("");
    try {
      const session = await createThreadWorkspace.mutateAsync(thread.id);
      navigate("/", {
        state: {
          batchSessionId: session.id,
          workspaceMode: "mail_batch",
          statusText:
            "已将这封来信载入完整工作台。可使用多角色草稿、Planner、批注重生成和版本回退；保存为已完成后会自动送达用户信箱。",
        },
      });
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "进入完整工作台失败");
    }
  }

  async function openAllPendingInWorkspace() {
    setMessage("");
    try {
      const session = await createThreadsWorkspace.mutateAsync();
      navigate("/", {
        state: {
          batchSessionId: session.id,
          workspaceMode: "mail_batch",
          statusText:
            "已将待回复书信批量载入完整工作台。逐条生成、编辑并保存为已完成后，会自动发送回对应用户信箱。",
        },
      });
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "创建书信批量工作台失败");
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto max-w-[1500px]">
        <header className="mb-6 flex flex-col gap-4 rounded-[20px] border border-line bg-white/80 px-5 py-4 shadow-card md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <img src={scirScLogo} alt="心灵笔友标志" className="h-20 w-28 object-contain mix-blend-multiply" />
            <div>
              <h1 className="font-serif text-3xl text-ink">分配给我的书信会话</h1>
              <p className="mt-1 text-sm text-ink/60">咨询师：{user?.displayName} · 共 {items.length} 段</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={openAllPendingInWorkspace}
              disabled={createThreadsWorkspace.isPending || items.length === 0 || items.every(isAnswered)}
              className="inline-flex items-center gap-2 rounded-full border border-amber/35 bg-mist/70 px-4 py-2 text-sm text-ink transition hover:bg-mist disabled:cursor-not-allowed disabled:opacity-45"
            >
              <Layers3 size={16} />
              {createThreadsWorkspace.isPending ? "创建中..." : "批量进入工作台"}
            </button>
            <Link to="/" className="inline-flex items-center gap-2 rounded-full border border-line bg-white/75 px-4 py-2 text-sm text-ink">
              <ArrowLeft size={16} />返回工作台
            </Link>
            <button type="button" onClick={() => { logout(); navigate("/login", { replace: true }); }} className="inline-flex items-center gap-2 rounded-full border border-line bg-white/75 px-4 py-2 text-sm text-ink">
              <LogOut size={16} />退出
            </button>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
          <aside className="rounded-[20px] border border-line bg-white/76 p-4 shadow-card">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink"><Inbox size={17} className="text-amber" />人工书信任务</div>
            <div className="grid gap-3">
              {items.length === 0 ? <p className="rounded-[16px] bg-paper/70 p-4 text-sm text-ink/60">暂时没有分配给你的书信。</p> : null}
              {items.map((item) => {
                const answered = isAnswered(item);
                const latest = latestUserMessage(item);
                const risk = threadRiskLevel(item);
                return (
                  <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className={`rounded-[16px] border p-4 text-left transition ${selected?.id === item.id ? "border-amber bg-[#F6F3FF]" : "border-line bg-white/70 hover:bg-white"}`}>
                    <div className="flex justify-between gap-3"><strong className="text-sm text-ink">任务 {taskNumbers.get(item.id) ?? 1}</strong><span className="text-xs text-ink/48">{item.status === "completed" ? "已完成" : answered ? "等待用户" : "待回复"}</span></div>
                    <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink/68">{latest?.content || item.title}</p>
                    <p className="mt-2 text-xs text-amber">希望：{item.response_preference || "未指定"} · {formatRelativeTime(item.updated_at)}</p>
                    <RiskChip level={risk} />
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="rounded-[20px] border border-line bg-white/76 p-6 shadow-card">
            {!selected ? <p className="text-sm text-ink/60">选择一段书信后开始回复。</p> : (
              <>
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div><p className="text-sm text-amber">用户署名：{selected.signature}</p><h2 className="mt-2 font-serif text-3xl text-ink">书信任务 {taskNumbers.get(selected.id) ?? 1}</h2></div>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-full bg-paper px-3 py-1 text-sm text-ink/64">回应偏好：{selected.response_preference || "未指定"}</span>
                    <button
                      type="button"
                      onClick={() => openThreadInWorkspace(selected)}
                      disabled={createThreadWorkspace.isPending}
                      className="inline-flex items-center gap-2 rounded-full border border-amber/35 bg-mist/70 px-3 py-1 text-sm text-ink transition hover:bg-mist disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <Wand2 size={15} />
                      {createThreadWorkspace.isPending ? "载入中..." : "进入完整工作台"}
                    </button>
                  </div>
                </div>
                {selected.memory?.summary ? (
                  <section className="mt-5 rounded-[16px] border border-line bg-[#F8F6FF] p-5">
                    <p className="text-sm font-semibold text-ink">系统记忆摘要</p>
                    <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-ink/68">{selected.memory.summary}</div>
                  </section>
                ) : null}
                <RiskReviewPanel assessment={latestUserRisk(selected)} level={threadRiskLevel(selected)} />
                <ThreadMessages messages={selected.messages} />
                <label className="mt-6 block text-sm font-semibold text-ink">写下一封回信
                  <textarea value={replyText} onChange={(event) => setReplyText(event.target.value)} placeholder={`请尽量按照“${selected.response_preference || "温柔陪伴"}”的方式回应，并参考上方完整往返记录...`} className="mt-3 min-h-[260px] w-full rounded-[16px] border border-line bg-white/78 px-5 py-5 text-[15px] leading-8 outline-none focus:border-amber" />
                </label>
                <AssistSafetyNotice review={assistDraft?.safety_review} />
                <div className="mt-5 flex items-center justify-between gap-4">
                  <p className="text-sm text-ink/60">{message}</p>
                  <div className="flex flex-wrap justify-end gap-3">
                    <button type="button" onClick={handleAssistDraft} disabled={assistLoading} className="inline-flex items-center gap-2 rounded-full border border-line bg-white/75 px-5 py-3 text-sm text-ink transition hover:bg-white disabled:opacity-45">
                      {assistLoading ? "起草中..." : "AI辅助起草"}
                    </button>
                    <button type="button" onClick={handleSubmit} disabled={submitReply.isPending || !replyText.trim()} className="lilac-gradient inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium text-white shadow-card disabled:opacity-45">
                      {isAnswered(selected) ? <CheckCircle2 size={16} /> : <Send size={16} />}
                      {submitReply.isPending ? "发送中..." : isAnswered(selected) ? "继续回信" : "发送回信"}
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function AssistSafetyNotice({ review }: { review?: SafetyReview }) {
  if (!review) return null;
  const safe = !review.replacement_used && !review.blocked && (!review.risk_level || review.risk_level === "NONE");
  return (
    <section className={`mt-4 rounded-[16px] border p-4 text-sm leading-7 ${safe ? "border-emerald-100 bg-emerald-50 text-emerald-900" : "border-red-200 bg-red-50 text-red-950"}`}>
      <p className="font-semibold">{safe ? "AI辅助草稿安全审核通过" : "AI辅助草稿需要重点复核"}</p>
      {review.signals?.slice(0, 3).map((signal) => <p key={signal}>• {signal}</p>)}
      {review.replacement_used ? <p>原始草稿命中高风险表达，系统已替换为安全回应。</p> : null}
    </section>
  );
}

function RiskChip({ level }: { level: RiskLevel }) {
  if (level === "NONE") return null;
  const styles: Record<RiskLevel, string> = {
    NONE: "",
    LOW: "bg-[#EEF2FF] text-[#4F46E5]",
    MEDIUM: "bg-[#FFF7ED] text-[#C2410C]",
    HIGH: "bg-[#FEF2F2] text-[#DC2626]",
    CRISIS: "bg-[#7F1D1D] text-white",
  };
  const labels: Record<RiskLevel, string> = {
    NONE: "正常",
    LOW: "低风险",
    MEDIUM: "中风险",
    HIGH: "高风险",
    CRISIS: "危机",
  };
  return <span className={`mt-3 inline-flex rounded-full px-3 py-1 text-xs font-medium ${styles[level]}`}>风险：{labels[level]}</span>;
}

function RiskReviewPanel({ assessment, level }: { assessment: RiskAssessment | null; level: RiskLevel }) {
  if (!assessment || level === "NONE") return null;
  const urgent = level === "HIGH" || level === "CRISIS";
  const labels: Record<RiskLevel, string> = {
    NONE: "正常",
    LOW: "低风险",
    MEDIUM: "中风险",
    HIGH: "高风险",
    CRISIS: "危机",
  };
  return (
    <section className={`mt-5 rounded-[16px] border p-5 ${urgent ? "border-red-200 bg-red-50 text-red-950" : "border-amber/30 bg-[#FFF7ED] text-ink/72"}`}>
      <p className="text-sm font-semibold">风险等级：{labels[level]}</p>
      <div className="mt-3 grid gap-1 text-sm leading-7">
        {assessment.signals.slice(0, 5).map((signal) => (
          <p key={signal}>• {signal}</p>
        ))}
      </div>
      {urgent ? (
        <div className="mt-4 rounded-[12px] bg-white/70 p-4 text-sm leading-7">
          <p className="font-semibold">回复前请重点确认：</p>
          <p>□ 是否存在自伤行为或自杀计划</p>
          <p>□ 是否能联系到现实中的支持者</p>
          <p>□ 是否需要建议立即联系紧急服务或专业危机热线</p>
        </div>
      ) : null}
    </section>
  );
}

function ThreadMessages({ messages }: { messages: MailMessage[] }) {
  const orderedMessages = [...messages].sort(
    (first, second) =>
      new Date(first.created_at).getTime() - new Date(second.created_at).getTime() || first.id - second.id,
  );
  return (
    <div className="mt-5 grid gap-4">
      {orderedMessages.map((message) => {
        const isUser = message.sender_type === "user";
        return (
          <article key={message.id} className={`rounded-[16px] p-5 text-[15px] leading-8 text-ink/76 ${isUser ? "bg-[#F8F6FF]" : "border border-line bg-paper/86"}`}>
            <p className="mb-2 text-sm font-semibold text-ink">{isUser ? "用户来信" : "咨询师回信"}</p>
            <div className="whitespace-pre-wrap">{message.content}</div>
            <p className="mt-3 text-xs text-ink/42">{formatRelativeTime(message.created_at)}</p>
          </article>
        );
      })}
    </div>
  );
}
