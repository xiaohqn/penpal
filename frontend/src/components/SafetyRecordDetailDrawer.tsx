/**
 * 输入：
 * - record：当前选中的安全回复记录详情；未选择时可能为 `undefined`。
 * 输出：
 * - 渲染安全回复记录的完整详情面板，包括安全对话评分、回复候选、整体修改说明、片段批注和版本历史。
 * 作用：
 * - 为安全回复样本库提供尽量接近普通对话历史记录的过程型详情展示。
 */
import type { SafetyRecordDetail } from "../features/safety-records/types";
import type { SafetyDialogueEvaluationScores } from "../features/safety/types";

type Props = {
  record: SafetyRecordDetail | undefined;
};

const SAFETY_EVALUATION_LABELS: Record<keyof SafetyDialogueEvaluationScores, string> = {
  risk_response_and_emergency_handling: "风险识别与紧急响应",
  supportive_nonjudgmental_attitude: "支持性与非评判态度",
  authentic_companionship: "真实陪伴感",
  human_presence_and_deep_empathy: "真实人类感与深度共情",
};

export function SafetyRecordDetailDrawer({ record }: Props) {
  const safetyEvaluationScores = record?.safety_evaluation?.scores ?? {};
  const safetyEvaluationEntries = Object.entries(SAFETY_EVALUATION_LABELS).map(([key, label]) => ({
    key: key as keyof SafetyDialogueEvaluationScores,
    label,
    score: safetyEvaluationScores[key as keyof SafetyDialogueEvaluationScores],
  }));
  const hasSafetyEvaluation = safetyEvaluationEntries.some((item) => typeof item.score === "number");

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
            <strong>选中来源</strong>
            <div className="mt-2 whitespace-pre-wrap">
              {record.selected_response_source_label || record.selected_response_source || "未记录来源"}
            </div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>润色回复</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.expert_polished_response}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>整体修改说明</strong>
            <div className="mt-2 whitespace-pre-wrap">{record.expert_annotation || "暂无说明"}</div>
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>安全对话评分</strong>
            {hasSafetyEvaluation ? (
              <div className="mt-3 grid gap-3">
                <div className="rounded-2xl bg-white/75 p-3 text-sm text-ink/78">
                  总分 {record.safety_evaluation?.total_score ?? "未汇总"} / 20
                  {typeof record.safety_evaluation?.average_score === "number"
                    ? `，均分 ${record.safety_evaluation.average_score}`
                    : ""}
                </div>
                <div className="grid gap-2">
                  {safetyEvaluationEntries.map((item) => (
                    <div key={item.key} className="flex items-center justify-between rounded-xl bg-white/75 px-3 py-2">
                      <span>{item.label}</span>
                      <span className="font-semibold text-ink">
                        {typeof item.score === "number" ? `${item.score} 分` : "未评分"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mt-2 whitespace-pre-wrap">暂无安全对话评分</div>
            )}
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>片段批注</strong>
            {record.source_annotations_json.length > 0 ? (
              <div className="mt-2 grid gap-3">
                {record.source_annotations_json.map((annotation, index) => (
                  <div key={annotation.id || `${annotation.start}-${annotation.end}-${index}`} className="rounded-2xl bg-white/75 p-3">
                    <div className="text-xs uppercase tracking-[0.16em] text-ink/42">片段批注 {index + 1}</div>
                    <div className="mt-2 whitespace-pre-wrap text-sm text-ink">
                      {annotation.quote || "未记录回复片段"}
                    </div>
                    <div className="mt-2 whitespace-pre-wrap text-sm text-ink/74">
                      {annotation.note || "暂无说明"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-2 whitespace-pre-wrap">暂无片段批注</div>
            )}
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>回复候选</strong>
            {record.safe_response_candidates_json.length > 0 ? (
              <div className="mt-2 grid gap-3">
                {record.safe_response_candidates_json.map((candidate) => (
                  <div key={`${candidate.source}-${candidate.source_label}`} className="rounded-2xl bg-white/75 p-3">
                    <div className="text-xs uppercase tracking-[0.16em] text-ink/42">
                      {candidate.source_label || candidate.source}
                    </div>
                    {candidate.intent ? (
                      <div className="mt-2 whitespace-pre-wrap text-sm text-ink/74">{candidate.intent}</div>
                    ) : null}
                    <div className="mt-2 whitespace-pre-wrap text-sm text-ink">
                      {candidate.safe_response}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-2 whitespace-pre-wrap">暂无候选记录</div>
            )}
          </section>
          <section className="rounded-3xl bg-paper/70 p-4">
            <strong>版本历史</strong>
            {record.response_versions_json.length > 0 ? (
              <div className="mt-2 grid gap-3">
                {record.response_versions_json
                  .slice()
                  .sort((a, b) => b.version_index - a.version_index)
                  .map((version) => (
                    <div
                      key={`${version.version_index}-${version.created_at}`}
                      className="rounded-2xl bg-white/75 p-3"
                    >
                      <div className="text-xs uppercase tracking-[0.16em] text-ink/42">
                        {version.label || `版本 ${version.version_index + 1}`} · {version.selected_response_source_label || version.selected_response_source || "未记录来源"}
                      </div>
                      {version.expert_annotation ? (
                        <div className="mt-2 whitespace-pre-wrap text-sm text-ink/74">
                          {version.expert_annotation}
                        </div>
                      ) : null}
                      {version.source_annotations.length > 0 ? (
                        <div className="mt-3 grid gap-2">
                          {version.source_annotations.map((annotation, annotationIndex) => (
                            <div
                              key={annotation.id || `${version.version_index}-${annotation.start}-${annotation.end}-${annotationIndex}`}
                              className="rounded-xl bg-paper/70 p-3"
                            >
                              <div className="text-xs uppercase tracking-[0.16em] text-ink/42">
                                本轮片段批注 {annotationIndex + 1}
                              </div>
                              <div className="mt-2 whitespace-pre-wrap text-sm text-ink">
                                {annotation.quote || "未记录回复片段"}
                              </div>
                              <div className="mt-2 whitespace-pre-wrap text-sm text-ink/74">
                                {annotation.note || "暂无说明"}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      <div className="mt-2 whitespace-pre-wrap text-sm text-ink">{version.response}</div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="mt-2 whitespace-pre-wrap">暂无版本历史</div>
            )}
          </section>
        </div>
      ) : (
        <p className="text-sm text-ink/60">点击左侧记录后，这里会展示完整详情。</p>
      )}
    </aside>
  );
}
