import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Clock3, Eye, History, LogOut, Mail, PenLine, Plus, Send, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../app/auth";
import scirScLogo from "../assets/logo-mark.png";
import { buildApiUrl } from "../lib/api-base";
import {
  useAddMailThreadMessage,
  useArchiveAiReplyToRecords,
  useCompleteMailThread,
  useCreateMailThread,
  useMailThreads,
  useUnarchiveAiReplyFromRecords,
} from "../features/mailThreads/hooks";
import type { MailMessage, MailThread, ResponsePreference, RiskAssessment, RiskLevel } from "../features/mailThreads/types";

type MailStatus = "writing" | "folding" | "sending" | "reading" | "replying" | "received";
type MailboxView = "inbox" | "compose" | "journey" | "detail";
type ReplyMode = "ai" | "human";
type InboxTab = "all" | "ai" | "human";

const RESPONSE_PREFERENCES: ResponsePreference[] = ["温柔陪伴", "理性分析", "启发引导"];
type ReplyViewState = "arrived" | "opening" | "unfolding" | "typing" | "done";
type PublicRuntimeConfig = {
  counselor_features_enabled: boolean;
};

const JOURNEY: Exclude<MailStatus, "writing">[] = ["folding", "sending", "reading", "replying", "received"];

const STATUS_COPY: Record<Exclude<MailStatus, "writing">, { title: string; body: string }> = {
  folding: {
    title: "正在封信",
    body: "正在把你的心事装进信封...",
  },
  sending: {
    title: "你的信正在路上",
    body: "信正在路上，请给它一点时间。",
  },
  reading: {
    title: "对方正在读",
    body: "心灵笔友正在认真读你的来信。",
  },
  replying: {
    title: "正在回信",
    body: "那些被认真接住的话，正在慢慢写成一封回信。",
  },
  received: {
    title: "回信送达",
    body: "你收到了一封回信。",
  },
};

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function splitReplyParagraphs(value: string) {
  return value
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function getOpenedReplyIds() {
  try {
    return new Set(JSON.parse(window.localStorage.getItem("mindful-opened-replies") || "[]") as number[]);
  } catch {
    return new Set<number>();
  }
}

function markReplyOpened(messageId: number) {
  const opened = getOpenedReplyIds();
  opened.add(messageId);
  window.localStorage.setItem("mindful-opened-replies", JSON.stringify([...opened]));
}

function openLatestReplyImmediately(thread: MailThread) {
  const replyMessage = getLatestReplyMessage(thread);
  if (replyMessage) {
    markReplyOpened(replyMessage.id);
  }
}

function getThreadStatus(item: MailThread) {
  if (item.status === "completed") {
    return "completed";
  }
  if (item.status === "waiting_counselor") {
    return "waiting_human";
  }
  if (item.reply_mode === "human") {
    return "human_replied";
  }
  if (item.status === "waiting_ai") {
    return "waiting_ai";
  }
  return "ai_replied";
}

function getLatestUserMessage(item: MailThread) {
  return [...item.messages].reverse().find((message) => message.sender_type === "user") ?? null;
}

function getLatestReplyMessage(item: MailThread) {
  return [...item.messages].reverse().find((message) => message.sender_type === "ai" || message.sender_type === "counselor") ?? null;
}

function getLatestUserRisk(item: MailThread) {
  return [...item.risk_assessments].reverse().find((assessment) => assessment.target_type === "user_letter") ?? null;
}

function riskRank(level: RiskLevel | string) {
  return { NONE: 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRISIS: 4 }[level as RiskLevel] ?? 0;
}

function precheckRisk(content: string): RiskLevel {
  const value = content.toLowerCase();
  if (["今晚准备", "已经准备好了", "买好了药", "遗书", "结束生命"].some((keyword) => value.includes(keyword))) {
    return "CRISIS";
  }
  if (["自杀", "想死", "不想活", "伤害自己", "自残", "割腕", "轻生"].some((keyword) => value.includes(keyword))) {
    return "HIGH";
  }
  if (["活着没意义", "撑不下去", "绝望", "长期失眠", "被家暴", "被虐待", "校园霸凌", "药物滥用"].some((keyword) => value.includes(keyword))) {
    return "MEDIUM";
  }
  return "NONE";
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

export function SlowMailboxPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const threadsQuery = useMailThreads();
  const createThread = useCreateMailThread();
  const addThreadMessage = useAddMailThreadMessage();
  const completeThread = useCompleteMailThread();
  const archiveAiReply = useArchiveAiReplyToRecords();
  const unarchiveAiReply = useUnarchiveAiReplyFromRecords();

  const [view, setView] = useState<MailboxView>("inbox");
  const [tab, setTab] = useState<InboxTab>("all");
  const [status, setStatus] = useState<MailStatus>("writing");
  const [replyMode, setReplyMode] = useState<ReplyMode>("ai");
  const [responsePreference, setResponsePreference] = useState<ResponsePreference>("温柔陪伴");
  const [letter, setLetter] = useState("");
  const [signature, setSignature] = useState(user?.displayName === "来访用户" ? "匿名" : user?.displayName ?? "匿名");
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");
  const [selectedThread, setSelectedThread] = useState<MailThread | null>(null);
  const [continuingThread, setContinuingThread] = useState<MailThread | null>(null);
  const [archivedReplyIds, setArchivedReplyIds] = useState<Record<number, number>>({});
  const [runtimeConfig, setRuntimeConfig] = useState<PublicRuntimeConfig>({ counselor_features_enabled: false });

  const items = threadsQuery.data?.items ?? [];
  const counselorFeaturesEnabled = runtimeConfig.counselor_features_enabled;
  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        if (tab === "all") return true;
        return tab === "ai" ? item.reply_mode === "ai" : item.reply_mode === "human";
      }),
    [items, tab],
  );
  const threadNumbers = useMemo(() => {
    const chronologicalItems = [...items].sort(
      (first, second) =>
        new Date(first.created_at).getTime() - new Date(second.created_at).getTime() || first.id - second.id,
    );
    return new Map(chronologicalItems.map((item, index) => [item.id, index + 1]));
  }, [items]);
  const statusIndex = useMemo(() => Math.max(0, JOURNEY.indexOf(status as Exclude<MailStatus, "writing">)), [status]);
  const canSend = letter.trim().length >= 8 && view === "compose";

  useEffect(() => {
    fetch(buildApiUrl("/api/v1/health"))
      .then((response) => response.json())
      .then((data) => {
        setRuntimeConfig({
          counselor_features_enabled: data?.counselor_features_enabled === true,
        });
      })
      .catch(() => {
        setRuntimeConfig({ counselor_features_enabled: false });
      });
  }, []);

  useEffect(() => {
    if (!counselorFeaturesEnabled && replyMode === "human") {
      setReplyMode("ai");
    }
    if (!counselorFeaturesEnabled && tab === "human") {
      setTab("all");
    }
  }, [counselorFeaturesEnabled, replyMode, tab]);

  function goInbox() {
    setView("inbox");
    setStatus("writing");
    setSelectedThread(null);
    setContinuingThread(null);
    setError("");
  }

  function startCompose() {
    setView("compose");
    setStatus("writing");
    setSelectedThread(null);
    setContinuingThread(null);
    setLetter("");
    setReply("");
    setError("");
  }

  function openDetail(item: MailThread) {
    setSelectedThread(item);
    setLetter(getLatestUserMessage(item)?.content ?? "");
    setSignature(item.signature);
    setReply(getLatestReplyMessage(item)?.content ?? "");
    setView("detail");
    setStatus("received");
    setError("");
  }

  function continueThread(item: MailThread) {
    setContinuingThread(item);
    setSelectedThread(null);
    setReplyMode(item.reply_mode);
    setResponsePreference(item.response_preference);
    setSignature(item.signature);
    setLetter("");
    setReply("");
    setError("");
    setStatus("writing");
    setView("compose");
  }

  async function handleDeliver() {
    if (!canSend) {
      setError("可以多写一点点，让心灵笔友更懂你。");
      return;
    }

    setError("");
    setReply("");
    setSelectedThread(null);
    setView("journey");

    const localRisk = precheckRisk(letter);
    const shouldForceHuman = counselorFeaturesEnabled && riskRank(localRisk) >= riskRank("HIGH");

    if (replyMode === "human" || shouldForceHuman) {
      try {
        if (shouldForceHuman) {
          setResponsePreference((current) => current || "温柔陪伴");
        }
        setStatus("folding");
        await wait(900);
        setStatus("sending");
        await wait(1300);
        setStatus("reading");
        await wait(900);
        const saved = continuingThread
          ? await addThreadMessage.mutateAsync({
              threadId: continuingThread.id,
              payload: { content: letter.trim() },
            })
          : await createThread.mutateAsync({
              signature: signature.trim() || "匿名",
              content: letter.trim(),
              reply_mode: "human",
              response_preference: responsePreference,
            });
        setSelectedThread(saved);
        setContinuingThread(null);
        setView("detail");
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "信件暂时没有投递成功，请稍后再试。");
        setView("compose");
      }
      return;
    }

    try {
      setStatus("folding");
      await wait(900);
      setStatus("sending");
      await wait(1700);
      setStatus("reading");
      await wait(1200);
      setStatus("replying");
      const [saved] = await Promise.all([
        continuingThread
          ? addThreadMessage.mutateAsync({
              threadId: continuingThread.id,
              payload: { content: letter.trim() },
            })
          : createThread.mutateAsync({
              signature: signature.trim() || "匿名",
              content: letter.trim(),
              reply_mode: "ai",
              response_preference: responsePreference,
            }),
        wait(1600),
      ]);
      setReply(getLatestReplyMessage(saved)?.content ?? "");
      setSelectedThread(saved);
      setContinuingThread(null);
      setStatus("received");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "回信暂时没有送达，请稍后再试。");
      setView("compose");
      setStatus("writing");
    }
  }

  return (
    <main className="mailbox-scene min-h-screen overflow-hidden px-4 py-6 md:px-8">
      <div className="mx-auto max-w-[1100px]">
        <MailboxHeader
          view={view}
          onBack={view === "inbox" ? undefined : goInbox}
          onCompose={startCompose}
          onLogout={() => {
            logout();
            navigate("/login", { replace: true });
          }}
        />

        {view === "inbox" ? (
          <InboxView
            items={filteredItems}
            loading={threadsQuery.isLoading}
            tab={tab}
            counselorFeaturesEnabled={counselorFeaturesEnabled}
            onTabChange={setTab}
            onOpen={openDetail}
            onCompose={startCompose}
          />
        ) : null}

        {view === "compose" ? (
          <ComposeView
            replyMode={replyMode}
            onReplyModeChange={setReplyMode}
            counselorFeaturesEnabled={counselorFeaturesEnabled}
            responsePreference={responsePreference}
            onResponsePreferenceChange={setResponsePreference}
            letter={letter}
            onLetterChange={setLetter}
            signature={signature}
            onSignatureChange={setSignature}
            canSend={canSend}
            error={error}
            onDeliver={handleDeliver}
          />
        ) : null}

        {view === "journey" ? <JourneyView status={status} statusIndex={statusIndex} /> : null}

        {view === "detail" && selectedThread ? (
          <DetailView
            item={selectedThread}
            threadNumber={threadNumbers.get(selectedThread.id) ?? 1}
            onBack={goInbox}
            onCompose={startCompose}
            markingComplete={completeThread.isPending}
            onContinue={() => continueThread(selectedThread)}
            onMarkComplete={async () => {
              const updated = await completeThread.mutateAsync(selectedThread.id);
              setSelectedThread(updated);
            }}
            archiveBusy={archiveAiReply.isPending || unarchiveAiReply.isPending}
            archivedRecordId={archivedReplyIds[selectedThread.id] ?? null}
            onToggleArchiveAiReply={async () => {
              const archivedRecordId = archivedReplyIds[selectedThread.id];
              if (archivedRecordId) {
                await unarchiveAiReply.mutateAsync(selectedThread.id);
                setArchivedReplyIds((current) => {
                  const next = { ...current };
                  delete next[selectedThread.id];
                  return next;
                });
                setError("已取消加入样本库，这封回信不会再作为 RAG 样本使用。");
                return;
              }
              const result = await archiveAiReply.mutateAsync(selectedThread.id);
              setArchivedReplyIds((current) => ({ ...current, [selectedThread.id]: result.record_id }));
              setError(`已加入样本库，记录 #${result.record_id}。谢谢你的反馈。`);
            }}
          />
        ) : null}

        {view === "journey" && status === "received" && selectedThread ? (
          <div className="relative z-10 mt-8 flex justify-center">
            <button
              type="button"
              onClick={() => {
                openLatestReplyImmediately(selectedThread);
                setView("detail");
              }}
              disabled={!getLatestReplyMessage(selectedThread)}
              className="lilac-gradient inline-flex items-center justify-center gap-2 rounded-full px-7 py-3 text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5"
            >
              <Sparkles size={16} />
              {getLatestReplyMessage(selectedThread) ? "打开回信" : "回信还在路上"}
            </button>
          </div>
        ) : null}
      </div>
    </main>
  );
}

function MailboxHeader({
  view,
  onBack,
  onCompose,
  onLogout,
}: {
  view: MailboxView;
  onBack?: () => void;
  onCompose: () => void;
  onLogout: () => void;
}) {
  return (
    <header className="relative z-10 flex flex-col gap-4 rounded-[20px] border border-line bg-white/74 px-5 py-4 shadow-card backdrop-blur md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-4">
        {onBack ? (
          <button
            type="button"
            onClick={onBack}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-line bg-white/75 text-ink transition hover:bg-white"
            aria-label="返回"
          >
            <ArrowLeft size={18} />
          </button>
        ) : null}
        <img src={scirScLogo} alt="心灵笔友标志" className="h-20 w-28 object-contain mix-blend-multiply" />
        <div>
          <h1 className="font-serif text-3xl text-ink">
            <span className="lilac-text">慢递信箱</span>
          </h1>
          <p className="mt-1 text-sm text-ink/60">
            {view === "inbox" ? "写信、等待、回信，都在这里。" : "把这一次通信慢慢完成。"}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onCompose}
          className="lilac-gradient inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5"
        >
          <Plus size={16} />
          写信
        </button>
        <button
          type="button"
          onClick={onLogout}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/70 px-4 py-3 text-sm text-ink transition hover:bg-paper/85"
        >
          <LogOut size={16} />
          退出
        </button>
      </div>
    </header>
  );
}

function InboxView({
  items,
  loading,
  tab,
  counselorFeaturesEnabled,
  onTabChange,
  onOpen,
  onCompose,
}: {
  items: MailThread[];
  loading: boolean;
  tab: InboxTab;
  counselorFeaturesEnabled: boolean;
  onTabChange: (tab: InboxTab) => void;
  onOpen: (item: MailThread) => void;
  onCompose: () => void;
}) {
  return (
    <section className="relative z-10 mt-6 rounded-[20px] border border-line bg-white/72 p-5 shadow-card backdrop-blur md:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="inline-flex rounded-full border border-line bg-paper/70 p-1">
          {[
            { value: "all", label: "全部" },
            { value: "ai", label: "AI回复" },
            ...(counselorFeaturesEnabled ? [{ value: "human", label: "人工回复" }] : []),
          ].map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => onTabChange(item.value as InboxTab)}
              className={`rounded-full px-4 py-2 text-sm transition ${
                tab === item.value ? "lilac-gradient text-white shadow-card" : "text-ink/72"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="text-sm text-ink/56">{loading ? "正在整理信箱..." : `共 ${items.length} 段书信`}</p>
      </div>

      <div className="mt-5 grid gap-4">
        {!loading && items.length === 0 ? (
          <div className="rounded-[20px] border border-dashed border-line bg-paper/62 px-5 py-10 text-center">
            <History size={24} className="mx-auto text-amber" />
            <h2 className="mt-4 font-serif text-2xl text-ink">还没有信件</h2>
            <p className="mt-2 text-sm text-ink/60">写下第一封信后，它和回信都会留在这里。</p>
            <button
              type="button"
              onClick={onCompose}
              className="lilac-gradient mt-5 inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium text-white shadow-card"
            >
              <PenLine size={16} />
              写第一封信
            </button>
          </div>
        ) : null}
        {items.map((item) => (
          <MailCard key={item.id} item={item} onOpen={() => onOpen(item)} />
        ))}
      </div>
    </section>
  );
}

function MailCard({ item, onOpen }: { item: MailThread; onOpen: () => void }) {
  const status = getThreadStatus(item);
  const latestUserMessage = getLatestUserMessage(item);
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`mail-card w-full rounded-[20px] border bg-white/82 p-5 text-left shadow-card transition hover:-translate-y-0.5 hover:bg-white ${
        status === "human_replied" ? "border-amber/40" : "border-line"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-ink">✉️ {item.title || "给心灵笔友"}</p>
            <p className="mt-3 line-clamp-2 text-[15px] leading-7 text-ink/72">
            {latestUserMessage?.content || "这段书信还在等待内容。"}
          </p>
        </div>
        <span className="shrink-0 text-xs text-ink/46">{formatRelativeTime(item.updated_at)}</span>
      </div>
      <div className="mt-4">
        <StatusTag status={status} item={item} />
        <RiskBadge assessment={getLatestUserRisk(item)} />
      </div>
    </button>
  );
}

function StatusTag({ status, item }: { status: string; item: MailThread }) {
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-[#ECFDF5] px-3 py-1 text-xs font-medium text-[#047857]">
        <CheckCircle2 size={14} />
        已完成
      </span>
    );
  }
  if (status === "waiting_human") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-[#FFF7ED] px-3 py-1 text-xs font-medium text-[#F59E0B]">
        <Clock3 size={14} />
        等待咨询师回复 · {formatRelativeTime(item.created_at)}
      </span>
    );
  }
  if (status === "waiting_ai") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-[#EEF2FF] px-3 py-1 text-xs font-medium text-[#4F46E5]">
        <Clock3 size={14} />
        AI正在写回信
      </span>
    );
  }
  if (status === "human_replied") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-[#F6F3FF] px-3 py-1 text-xs font-medium text-[#8B5CF6]">
        📩 咨询师已回信
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-[#EDE9FE] px-3 py-1 text-xs font-medium text-[#6D5AE6]">
      🤖 AI已回复 · {formatRelativeTime(item.updated_at)}
    </span>
  );
}

function RiskBadge({ assessment }: { assessment: RiskAssessment | null }) {
  if (!assessment || riskRank(assessment.risk_level) < riskRank("HIGH")) {
    return null;
  }
  return (
    <span className="mt-2 inline-flex rounded-full bg-[#F6F3FF] px-3 py-1 text-xs font-medium text-[#6D5AE6]">
      已优先送达
    </span>
  );
}

function ComposeView({
  replyMode,
  onReplyModeChange,
  counselorFeaturesEnabled,
  responsePreference,
  onResponsePreferenceChange,
  letter,
  onLetterChange,
  signature,
  onSignatureChange,
  canSend,
  error,
  onDeliver,
}: {
  replyMode: ReplyMode;
  onReplyModeChange: (mode: ReplyMode) => void;
  counselorFeaturesEnabled: boolean;
  responsePreference: ResponsePreference;
  onResponsePreferenceChange: (preference: ResponsePreference) => void;
  letter: string;
  onLetterChange: (value: string) => void;
  signature: string;
  onSignatureChange: (value: string) => void;
  canSend: boolean;
  error: string;
  onDeliver: () => void;
}) {
  return (
    <section className="relative z-10 mt-6 grid gap-6">
      <div className="grid gap-4 md:grid-cols-2">
        <ComposeSelector
          active={replyMode === "ai"}
          icon="🤖"
          title="AI即时回复"
          subtitle="即时反馈，适合当下先被接住"
          onClick={() => onReplyModeChange("ai")}
        />
        <ComposeSelector
          active={replyMode === "human"}
          icon="👩‍⚕️"
          title="人工回复"
          subtitle={counselorFeaturesEnabled ? "需要等待，适合更认真地交给咨询师" : "当前暂未开放人工回复"}
          disabled={!counselorFeaturesEnabled}
          onClick={() => onReplyModeChange("human")}
        />
      </div>

      <section className="rounded-[20px] border border-line bg-white/76 p-5 shadow-card">
          <h3 className="font-serif text-2xl text-ink">你更希望这封信被怎样回应？</h3>
          <p className="mt-2 text-sm text-ink/60">
            {replyMode === "ai"
              ? "AI会按这个回应方式生成一封完整回信。"
              : "这个偏好会和来信一起交给系统随机分配的咨询师。"}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {RESPONSE_PREFERENCES.map((preference) => (
              <button
                key={preference}
                type="button"
                onClick={() => onResponsePreferenceChange(preference)}
                className={`rounded-[16px] border px-4 py-3 text-sm transition ${
                  responsePreference === preference
                    ? "border-amber bg-[#F6F3FF] font-medium text-ink shadow-card"
                    : "border-line bg-white/70 text-ink/68 hover:bg-white"
                }`}
              >
                {preference}
              </button>
            ))}
          </div>
        </section>

      <div className="letter-paper rounded-[20px] border border-line bg-white/84 p-6 shadow-card md:p-8">
        <p className="text-sm uppercase tracking-[0.2em] text-amber">Dear Mindful Penpal</p>
        <h2 className="mt-2 font-serif text-3xl text-ink">今晚想写给心灵笔友的话</h2>
        <textarea
          value={letter}
          onChange={(event) => onLetterChange(event.target.value)}
          placeholder={"今天让你最难受的一刻是什么？\n你可以慢慢说，不用一次说完。"}
          className="mt-5 min-h-[360px] w-full rounded-[16px] border border-line bg-white/76 px-6 py-6 text-[16px] leading-7 text-ink outline-none transition focus:border-amber focus:bg-white focus:shadow-[0_0_0_4px_rgba(139,92,246,0.12)]"
        />
        <div className="mt-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <label className="text-sm text-ink/68">
            署名
            <input
              value={signature}
              onChange={(event) => onSignatureChange(event.target.value)}
              className="ml-3 rounded-full border border-line bg-paper/70 px-4 py-2 text-ink outline-none focus:border-amber"
            />
          </label>
          <button
            type="button"
            onClick={onDeliver}
            disabled={!canSend}
            className="lilac-gradient inline-flex h-12 w-[220px] items-center justify-center gap-2 rounded-full text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5 hover:shadow-[0_10px_30px_rgba(139,92,246,0.2)] disabled:cursor-not-allowed disabled:opacity-45"
          >
            <Send size={16} />
            投递这封信
          </button>
        </div>
        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
      </div>
    </section>
  );
}

function ComposeSelector({
  active,
  icon,
  title,
  subtitle,
  disabled = false,
  onClick,
}: {
  active: boolean;
  icon: string;
  title: string;
  subtitle: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-[20px] border p-5 text-left shadow-card transition disabled:cursor-not-allowed disabled:opacity-45 ${
        active ? "scale-[1.02] border-amber bg-[#F6F3FF]" : "border-line bg-white/76 hover:bg-white disabled:hover:bg-white/76"
      }`}
    >
      <span className="text-2xl">{icon}</span>
      <p className="mt-3 text-base font-semibold text-ink">{title}</p>
      <p className="mt-1 text-sm leading-6 text-ink/60">{subtitle}</p>
    </button>
  );
}

function JourneyView({ status, statusIndex }: { status: MailStatus; statusIndex: number }) {
  return (
    <section className="relative z-10 mt-6 rounded-[20px] border border-line bg-white/72 p-6 shadow-card backdrop-blur md:p-8">
      <MailJourney status={status} statusIndex={statusIndex} />
    </section>
  );
}

function DetailView({
  item,
  threadNumber,
  onBack,
  onCompose,
  onContinue,
  markingComplete,
  onMarkComplete,
  archiveBusy,
  archivedRecordId,
  onToggleArchiveAiReply,
}: {
  item: MailThread;
  threadNumber: number;
  onBack: () => void;
  onCompose: () => void;
  onContinue: () => void;
  markingComplete: boolean;
  onMarkComplete: () => void;
  archiveBusy: boolean;
  archivedRecordId: number | null;
  onToggleArchiveAiReply: () => void;
}) {
  const status = getThreadStatus(item);
  const hasAiReply = item.messages.some((message) => message.sender_type === "ai");
  return (
    <section className="relative z-10 mt-6 rounded-[20px] border border-line bg-white/76 p-6 shadow-card backdrop-blur md:p-8">
      <div className="flex flex-col gap-4 border-b border-line pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <button type="button" onClick={onBack} className="inline-flex items-center gap-2 text-sm text-ink/62">
            <ArrowLeft size={16} />
            返回信箱
          </button>
          <h2 className="mt-3 font-serif text-3xl text-ink">第 {threadNumber} 段书信</h2>
        </div>
        <StatusTag status={status} item={item} />
      </div>

      <div className="mt-6">
        <MailTimeline status={status} />
      </div>

      <RiskPanel assessment={getLatestUserRisk(item)} />

      {item.reply_mode === "human" ? (
        <section className="mt-4 rounded-[16px] border border-line bg-white/72 p-5 text-sm text-ink/68">
          <p>希望被回应的方式：<strong className="text-ink">{item.response_preference || "未指定"}</strong></p>
          <p className="mt-2">已分配咨询师：<strong className="text-ink">{item.assigned_counselor_id || "正在分配"}</strong></p>
        </section>
      ) : null}

      <div className="my-6 border-t border-line" />

      <ThreadTimeline messages={item.messages} waiting={status === "waiting_human"} />

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onContinue}
          disabled={item.status === "completed"}
          className="lilac-gradient inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium text-white shadow-card disabled:cursor-not-allowed disabled:opacity-55"
        >
          <PenLine size={16} />
          继续写给 TA
        </button>
        <button
          type="button"
          onClick={onCompose}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/75 px-5 py-3 text-sm text-ink transition hover:bg-white"
        >
          <Plus size={16} />
          开始新的书信
        </button>
        <button
          type="button"
          onClick={onMarkComplete}
          disabled={item.status === "completed" || markingComplete}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white/75 px-5 py-3 text-sm text-ink transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-55"
        >
          <CheckCircle2 size={16} />
          {markingComplete ? "标记中..." : item.status === "completed" ? "已完成" : "标记完成"}
        </button>
        {hasAiReply ? (
          <button
            type="button"
            onClick={onToggleArchiveAiReply}
            disabled={archiveBusy}
            className={`inline-flex items-center justify-center gap-2 rounded-full border px-5 py-3 text-sm transition disabled:cursor-not-allowed disabled:opacity-55 ${
              archivedRecordId
                ? "border-[#047857]/25 bg-[#ECFDF5] text-[#047857] hover:bg-white"
                : "border-amber/35 bg-[#F6F3FF] text-ink hover:bg-white"
            }`}
          >
            {archivedRecordId ? <CheckCircle2 size={16} /> : <Sparkles size={16} />}
            {archiveBusy
              ? archivedRecordId
                ? "取消中..."
                : "加入中..."
              : archivedRecordId
                ? "已加入样本库，点击取消"
                : "满意，加入样本库"}
          </button>
        ) : null}
      </div>
    </section>
  );
}

function RiskPanel({ assessment }: { assessment: RiskAssessment | null }) {
  if (!assessment || riskRank(assessment.risk_level) < riskRank("HIGH")) {
    return null;
  }
  const isCrisis = assessment.risk_level === "CRISIS";
  return (
    <section className={`mt-4 rounded-[16px] border p-5 text-sm leading-7 ${isCrisis ? "border-red-100 bg-red-50 text-red-950" : "border-amber/30 bg-[#FFF7ED] text-ink/72"}`}>
      <p className="font-semibold">{isCrisis ? "先照顾此刻的安全" : "你的来信已经被优先送达"}</p>
      <p className="mt-2">
        {isCrisis
          ? "你写下的内容很重要。在等待回信前，如果你此刻可能伤害自己，请先不要独处，立刻联系身边可信赖的人或当地紧急服务。"
          : "因为你写下的内容很重要，这封信会被更谨慎地阅读和回应。请给心灵笔友一点时间。"}
      </p>
    </section>
  );
}

function MailTimeline({ status }: { status: string }) {
  const steps = [
    { key: "delivered", label: "已送达" },
    { key: "read", label: "已阅读" },
    { key: "writing", label: "撰写中" },
    { key: "replied", label: "已回复" },
  ];
  const activeCount = status === "waiting_human" ? 1 : 4;
  return (
    <div className="grid grid-cols-4 gap-2">
      {steps.map((step, index) => (
        <div key={step.key} className="flex items-center gap-2">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-xs ${
              index < activeCount ? "lilac-gradient text-white" : "bg-paper text-ink/42"
            } ${status === "waiting_human" && index === 1 ? "pulse-soft" : ""}`}
          >
            ●
          </div>
          <span className={`text-xs ${index < activeCount ? "text-ink" : "text-ink/42"}`}>{step.label}</span>
        </div>
      ))}
    </div>
  );
}

function ThreadTimeline({
  messages,
  waiting,
}: {
  messages: MailMessage[];
  waiting: boolean;
}) {
  const orderedMessages = [...messages].sort(
    (first, second) =>
      new Date(first.created_at).getTime() - new Date(second.created_at).getTime() || first.id - second.id,
  );
  const visibleMessages = orderedMessages.filter((message, index) => {
    if (message.sender_type === "user") return true;
    const previous = orderedMessages[index - 1];
    return !(
      previous &&
      previous.sender_type === message.sender_type &&
      previous.content.trim() === message.content.trim() &&
      Math.abs(new Date(message.created_at).getTime() - new Date(previous.created_at).getTime()) < 120000
    );
  });
  return (
    <div className="grid gap-5">
      {visibleMessages.map((message, index) => {
        const isUser = message.sender_type === "user";
        if (!isUser) {
          return <ReplyBlock key={message.id} message={message} />;
        }
        return (
          <section
            key={message.id}
            className={`rounded-[16px] border p-5 ${
              isUser ? "border-line bg-[#F8F6FF]" : "border-line bg-paper/86"
            }`}
          >
            <p className="text-sm font-semibold text-ink">
              {isUser ? `你的第 ${visibleMessages.slice(0, index + 1).filter((item) => item.sender_type === "user").length} 封来信` : "收到的回信"}
            </p>
            <div className="mt-3 whitespace-pre-wrap text-[15px] leading-8 text-ink/76">{message.content}</div>
            <p className="mt-3 text-xs text-ink/42">{formatRelativeTime(message.created_at)}</p>
          </section>
        );
      })}
      {waiting ? (
        <section className="rounded-[16px] border border-line bg-white/72 p-6 text-center">
          <Clock3 size={22} className="mx-auto text-[#F59E0B]" />
          <h3 className="mt-3 font-serif text-2xl text-ink">正在等待回复</h3>
          <p className="mx-auto mt-2 max-w-md text-sm leading-7 text-ink/62">
            你的信已经被认真接收，对方正在阅读这一整段往返记录。
          </p>
        </section>
      ) : null}
    </div>
  );
}

function ReplyBlock({ message }: { message: MailMessage }) {
  const alreadyOpened = getOpenedReplyIds().has(message.id);
  const [replyState, setReplyState] = useState<ReplyViewState>(alreadyOpened ? "done" : "arrived");
  const [typedParagraphs, setTypedParagraphs] = useState<string[]>(alreadyOpened ? splitReplyParagraphs(message.content) : []);
  const [activeText, setActiveText] = useState("");
  const paragraphs = useMemo(() => splitReplyParagraphs(message.content), [message.content]);

  useEffect(() => {
    const opened = getOpenedReplyIds().has(message.id);
    setReplyState(opened ? "done" : "arrived");
    setTypedParagraphs(opened ? splitReplyParagraphs(message.content) : []);
    setActiveText("");
  }, [message.content, message.id]);

  useEffect(() => {
    if (replyState !== "typing") {
      return;
    }

    let cancelled = false;
    async function typeParagraphs() {
      const completed: string[] = [];
      for (const paragraph of paragraphs) {
        let current = "";
        for (const char of paragraph) {
          if (cancelled) {
            return;
          }
          current += char;
          setActiveText(current);
          await wait(28);
        }
        completed.push(paragraph);
        setTypedParagraphs([...completed]);
        setActiveText("");
        await wait(360);
      }
      if (!cancelled) {
        markReplyOpened(message.id);
        setReplyState("done");
      }
    }

    void typeParagraphs();
    return () => {
      cancelled = true;
    };
  }, [paragraphs, replyState]);

  async function openReply() {
    markReplyOpened(message.id);
    setReplyState("opening");
    await wait(700);
    setReplyState("unfolding");
    await wait(760);
    setReplyState("typing");
  }

  if (replyState === "arrived" || replyState === "opening") {
    return (
      <section className="reply-arrival rounded-[20px] border border-line bg-white/72 p-8 text-center shadow-card">
        <div className="mailbox-glow mx-auto mb-5 flex h-24 w-24 items-center justify-center rounded-[28px] bg-paper/80">
          <div className={`reply-envelope ${replyState === "opening" ? "reply-envelope-opening" : ""}`}>
            <div className="reply-envelope-flap" />
          </div>
        </div>
        <h3 className="font-serif text-3xl text-ink">你收到了一封回信</h3>
        <p className="mx-auto mt-3 max-w-md text-sm leading-7 text-ink/62">
          它已经轻轻落进信箱。准备好时，再慢慢打开。
        </p>
        <button
          type="button"
          onClick={openReply}
          disabled={replyState === "opening"}
          className="lilac-gradient mt-6 inline-flex items-center justify-center gap-2 rounded-full px-7 py-3 text-sm font-medium text-white shadow-card transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-70"
        >
          <Sparkles size={16} />
          {replyState === "opening" ? "正在打开..." : "打开回信"}
        </button>
      </section>
    );
  }

  return (
    <section
      className={`reply-paper reply-unfold rounded-[16px] border border-line bg-paper/86 p-6 ${
        replyState === "unfolding" ? "reply-unfolding" : ""
      }`}
    >
      <p className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-ink">
        <Eye size={16} className="text-amber" />
        收到的回信
      </p>
      {replyState === "unfolding" ? (
        <div className="min-h-40 text-sm leading-7 text-ink/54">信纸正在展开...</div>
      ) : (
        <div className="typewriter-reply min-h-40 text-[15px] leading-8 text-ink">
          {typedParagraphs.map((paragraph, index) => (
            <p key={`${paragraph}-${index}`} className="mb-5 whitespace-pre-wrap">
              {paragraph}
            </p>
          ))}
          {replyState === "typing" ? (
            <p className="mb-5 whitespace-pre-wrap">
              {activeText}
              <span className="typing-cursor">|</span>
            </p>
          ) : null}
          {replyState === "done" && typedParagraphs.length === 0 ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : null}
        </div>
      )}
    </section>
  );
}

function MailJourney({ status, statusIndex }: { status: MailStatus; statusIndex: number }) {
  const copy = STATUS_COPY[status as Exclude<MailStatus, "writing">];
  return (
    <div className="mail-journey relative min-h-[520px] overflow-hidden rounded-[20px] bg-[linear-gradient(180deg,rgba(248,250,255,0.9),rgba(255,246,252,0.78))] px-5 py-8">
      <div className="floating-lights" />
      <div className="relative z-10 text-center">
        <p className="text-sm uppercase tracking-[0.22em] text-amber">Mail Journey</p>
        <h2 className="mt-3 font-serif text-4xl text-ink">{copy.title}</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-ink/66">{copy.body}</p>
      </div>

      <div className="mail-route" aria-hidden="true">
        <svg viewBox="0 0 760 240" className="absolute inset-x-0 top-24 mx-auto h-64 w-full max-w-4xl">
          <path
            d="M60 168 C 190 42, 292 236, 408 128 S 626 58, 704 156"
            fill="none"
            stroke="rgba(154,123,232,0.26)"
            strokeWidth="4"
            strokeDasharray="10 12"
            strokeLinecap="round"
          />
        </svg>
        <div className={`traveler traveler-${status}`}>
          <div className="envelope-shape">
            <div className="envelope-flap" />
          </div>
        </div>
        <div className="mailbox mailbox-left">信箱</div>
        <div className="mailbox mailbox-right">回信</div>
      </div>

      <div className="relative z-10 mt-[330px] grid gap-3 md:grid-cols-5">
        {JOURNEY.map((step, index) => (
          <div
            key={step}
            className={`rounded-[20px] border px-4 py-3 text-sm ${
              index <= statusIndex ? "border-amber/40 bg-white/82 text-ink" : "border-line bg-white/45 text-ink/48"
            }`}
          >
            <p className="font-semibold">{STATUS_COPY[step].title}</p>
            <p className="mt-1 text-xs leading-5">{index <= statusIndex ? "已抵达" : "等待中"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
