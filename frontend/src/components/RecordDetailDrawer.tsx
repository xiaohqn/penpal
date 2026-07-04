import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import type { RecordDetail, UpdateRecordPayload } from "../features/records/types";

type Props = {
  record: RecordDetail | undefined;
  onSave?: (recordId: number, payload: UpdateRecordPayload) => Promise<void>;
  saving?: boolean;
};

function formatDateTime(value: string) {
  if (!value) return "暂无";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function stringifyJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function parseJsonObject(value: string, fieldName: string) {
  const parsed = JSON.parse(value || "{}");
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${fieldName} 必须是 JSON 对象`);
  }
  return parsed as Record<string, unknown>;
}

function ragReadyLabel(value: string) {
  if (value === "approved") return "进入 RAG 素材库";
  if (value === "rejected") return "不进入 RAG 素材库";
  return "待判断";
}

export function RecordDetailDrawer({ record, onSave, saving = false }: Props) {
  const [userInput, setUserInput] = useState("");
  const [expertPolishedResponse, setExpertPolishedResponse] = useState("");
  const [expertAnnotation, setExpertAnnotation] = useState("");
  const [ragReady, setRagReady] = useState("pending");
  const [sampleReason, setSampleReason] = useState("");
  const [evaluationJson, setEvaluationJson] = useState("{}");
  const [sampleTagsJson, setSampleTagsJson] = useState("{}");
  const [plannerLabelsJson, setPlannerLabelsJson] = useState("{}");
  const [message, setMessage] = useState("");

  useEffect(() => {
    setUserInput(record?.user_input ?? "");
    setExpertPolishedResponse(record?.expert_polished_response ?? "");
    setExpertAnnotation(record?.expert_annotation ?? "");
    setRagReady(record?.rag_ready ?? "pending");
    setSampleReason(record?.sample_reason ?? "");
    setEvaluationJson(stringifyJson(record?.evaluation_json ?? {}));
    setSampleTagsJson(stringifyJson(record?.sample_tags_json ?? {}));
    setPlannerLabelsJson(stringifyJson(record?.planner_labels_json ?? {}));
    setMessage("");
  }, [record]);

  async function handleSave() {
    if (!record || !onSave) return;
    try {
      await onSave(record.id, {
        user_input: userInput,
        expert_polished_response: expertPolishedResponse,
        expert_annotation: expertAnnotation,
        rag_ready: ragReady,
        sample_reason: sampleReason,
        evaluation: parseJsonObject(evaluationJson, "回复评分"),
        sample_tags: parseJsonObject(sampleTagsJson, "样本标签"),
        planner_labels: parseJsonObject(plannerLabelsJson, "Planner 标签"),
      });
      setMessage("已保存修改。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败");
    }
  }

  return (
    <aside className="rounded-panel border border-line bg-white/78 p-5 shadow-soft">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-moss">记录详情</p>
          <h2 className="mt-1 font-serif text-2xl text-ink">
            {record ? `#${record.id}` : "选择一条记录"}
          </h2>
          {record ? (
            <p className="mt-1 text-sm leading-6 text-ink/56">
              咨询师 ID：{record.counselor_id} · 创建：{formatDateTime(record.created_at)} · 更新：{formatDateTime(record.updated_at)}
            </p>
          ) : null}
        </div>
        {record ? (
          <button
            type="button"
            onClick={handleSave}
            disabled={!onSave || saving}
            className="rounded-full bg-amber px-4 py-2 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-amber/45"
          >
            {saving ? "保存中..." : "保存修改"}
          </button>
        ) : null}
      </div>
      {message ? <p className="mb-3 rounded-2xl bg-paper/72 px-3 py-2 text-sm text-ink/68">{message}</p> : null}

      {record ? (
        <div className="grid gap-4 text-sm leading-7 text-ink/82">
          <EditableBlock title="用户来信">
            <textarea
              value={userInput}
              onChange={(event) => setUserInput(event.target.value)}
              className="min-h-[150px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 text-sm leading-7 text-ink outline-none focus:border-amber"
            />
          </EditableBlock>
          <EditableBlock title="最终回复">
            <textarea
              value={expertPolishedResponse}
              onChange={(event) => setExpertPolishedResponse(event.target.value)}
              className="min-h-[220px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 text-sm leading-7 text-ink outline-none focus:border-amber"
            />
          </EditableBlock>

          <EditableBlock title="专家批注">
            <textarea
              value={expertAnnotation}
              onChange={(event) => setExpertAnnotation(event.target.value)}
              placeholder="补写专家判断、修改依据，或说明是否建议进入 RAG。"
              className="min-h-[110px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 text-sm leading-7 text-ink outline-none focus:border-amber"
            />
          </EditableBlock>

          <EditableBlock title="回复评分">
            <textarea
              value={evaluationJson}
              onChange={(event) => setEvaluationJson(event.target.value)}
              className="min-h-[150px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 font-mono text-xs leading-6 text-ink outline-none focus:border-amber"
            />
          </EditableBlock>

          <EditableBlock title="沉淀状态">
            <div className="grid gap-3">
              <select
                value={ragReady}
                onChange={(event) => setRagReady(event.target.value)}
                className="rounded-2xl border border-line bg-white/78 px-3 py-2 text-sm text-ink outline-none focus:border-amber"
              >
                <option value="pending">待判断</option>
                <option value="approved">进入 RAG 素材库</option>
                <option value="rejected">不进入 RAG 素材库</option>
              </select>
              <p className="text-xs text-ink/52">当前：{ragReadyLabel(ragReady)}</p>
              <textarea
                value={sampleReason}
                onChange={(event) => setSampleReason(event.target.value)}
                placeholder="可选：说明为什么适合或不适合进入 RAG 素材库。"
                className="min-h-[78px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 text-sm leading-7 text-ink outline-none focus:border-amber"
              />
            </div>
          </EditableBlock>

          <EditableBlock title="样本标签">
            <textarea
              value={sampleTagsJson}
              onChange={(event) => setSampleTagsJson(event.target.value)}
              className="min-h-[130px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 font-mono text-xs leading-6 text-ink outline-none focus:border-amber"
            />
          </EditableBlock>

          <details className="rounded-3xl bg-paper/60 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-ink">其他信息</summary>
            <div className="mt-3 grid min-w-0 gap-3">
              <JsonDetails title="Planner 输出" value={record.planner_output_json} />
              <JsonDetails title="Planner 标签" value={plannerLabelsJson} editable onChange={setPlannerLabelsJson} />
              <ReadOnlyDetails title="AI 选中草稿" content={record.ai_selected_raw_response} />
              <JsonDetails title="风险评估" value={record.risk_assessment_json ?? {}} />
              <JsonDetails title="样本快照" value={record.sample_snapshot_json ?? {}} />
            </div>
          </details>
        </div>
      ) : (
        <p className="text-sm text-ink/60">点击左侧记录后，这里会展示完整详情。</p>
      )}
    </aside>
  );
}

function EditableBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-line bg-paper/70 p-4">
      <strong>{title}</strong>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function ReadOnlyDetails({ title, content }: { title: string; content: string }) {
  return (
    <details className="min-w-0 rounded-2xl border border-line bg-white/68 p-3">
      <summary className="cursor-pointer text-sm font-semibold text-ink">{title}</summary>
      <div className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap text-sm leading-7 text-ink/76">{content || "暂无"}</div>
    </details>
  );
}

function JsonDetails({
  title,
  value,
  editable = false,
  onChange,
}: {
  title: string;
  value: unknown;
  editable?: boolean;
  onChange?: (value: string) => void;
}) {
  return (
    <details className="min-w-0 rounded-2xl border border-line bg-white/68 p-3">
      <summary className="cursor-pointer text-sm font-semibold text-ink">{title}</summary>
      {editable ? (
        <textarea
          value={String(value)}
          onChange={(event) => onChange?.(event.target.value)}
          className="mt-2 min-h-[120px] w-full resize-y rounded-2xl border border-line bg-white/80 px-3 py-2 font-mono text-xs leading-6 text-ink outline-none focus:border-amber"
        />
      ) : (
        <pre className="mt-2 max-h-72 max-w-full overflow-auto rounded-2xl bg-paper/72 p-3 text-xs leading-6 text-ink/76">
{stringifyJson(value)}
        </pre>
      )}
    </details>
  );
}
