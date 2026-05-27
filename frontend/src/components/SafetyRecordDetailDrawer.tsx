/**
 * 输入：
 * - record：当前选中的安全回复记录详情；未选择时可能为 `undefined`。
 * 输出：
 * - 渲染安全回复记录的完整详情面板。
 * 作用：
 * - 为安全回复样本库提供独立的右侧详情展示。
 */
import type { SafetyRecordDetail } from "../features/safety-records/types";

type Props = {
  record: SafetyRecordDetail | undefined;
};

export function SafetyRecordDetailDrawer({ record }: Props) {
  return (
    <aside className="rounded-panel border border-line bg-white/78 p-6 shadow-soft">
      <div className="mb-4">
        <p className="text-sm uppercase tracking-[0.22em] text-moss">安全回复详情</p>
        <h2 className="mt-1 font-serif text-2xl text-ink">
          {record ? `#${record.id} · ${record.style_name}` : "选择一条安全回复记录"}
        </h2>
      </div>
      {record ? (
        <div className="grid gap-4 text-sm leading-7 text-ink/82">
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>原始来信</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.user_input}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>风险类型</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.risk_labels_json.join(" / ")}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>修正类型</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {record.corrected_risk_labels_json.join(" / ")}
            </div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>风险原因</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.risk_reason}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>原始回复</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.ai_safe_response}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>润色回复</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.expert_polished_response}</div>
          </section>
        </div>
      ) : (
        <p className="text-sm text-ink/60">点击左侧记录后，这里会展示完整详情。</p>
      )}
    </aside>
  );
}
