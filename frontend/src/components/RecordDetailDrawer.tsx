import type { RecordDetail } from "../features/records/types";

type Props = {
  record: RecordDetail | undefined;
};

export function RecordDetailDrawer({ record }: Props) {
  return (
    <aside className="rounded-panel border border-line bg-white/78 p-6 shadow-soft">
      <div className="mb-4">
        <p className="text-sm uppercase tracking-[0.22em] text-moss">记录详情</p>
        <h2 className="mt-1 font-serif text-2xl text-ink">
          {record ? `#${record.id} · ${record.selected_persona_name}` : "选择一条记录"}
        </h2>
      </div>
      {record ? (
        <div className="grid gap-4 text-sm leading-7 text-ink/82">
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>原始来信</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.user_input}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>Planner 输出</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {JSON.stringify(record.planner_output_json, null, 2)}
            </div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>AI 选中草稿</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.ai_selected_raw_response}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>专家润色稿</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.expert_polished_response}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>整体修改说明</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.expert_annotation || "暂无说明"}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>回复评分</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {JSON.stringify(record.evaluation_json ?? {}, null, 2)}
            </div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>沉淀状态</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {record.rag_ready === "approved" ? "已记录处理过程与满意版本" : "当前主要保存了最终版本，尚未形成完整批注沉淀"}
            </div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>样本标签</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {JSON.stringify(record.sample_tags_json ?? {}, null, 2)}
            </div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>Planner 标签</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {JSON.stringify(record.planner_labels_json ?? {}, null, 2)}
            </div>
          </section>
        </div>
      ) : (
        <p className="text-sm text-ink/60">点击左侧记录后，这里会展示完整详情。</p>
      )}
    </aside>
  );
}
