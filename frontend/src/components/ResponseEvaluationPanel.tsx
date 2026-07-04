import type {
  EvaluationSafetyChecks,
  EvaluationSafetyNotes,
  EvaluationScores,
  ResponseEvaluation,
} from "../features/records/types";

type MetricKey = keyof EvaluationScores;
type SafetyCheckKey = keyof EvaluationSafetyChecks;

type RubricLevel = {
  score: number;
  label: string;
  description: string;
};

type RubricMetric = {
  key: MetricKey;
  title: string;
  levels: RubricLevel[];
};

type LegacyEvaluationScores = Partial<{
  intent_safety: number;
  authentic_empathy: number;
  grounded_guidance: number;
  narrative_companionship: number;
}>;

type Props = {
  value: ResponseEvaluation;
  onChange: (value: ResponseEvaluation) => void;
  defaultOpen?: boolean;
};

export const RUBRIC_VERSION = "response_quality_v2";

export const EMPTY_EVALUATION: ResponseEvaluation = {
  rubric_version: RUBRIC_VERSION,
  scores: {},
  safety_checks: {},
  safety_notes: {},
};

const RUBRIC_METRICS: RubricMetric[] = [
  {
    key: "problem_risk_recognition",
    title: "问题识别与风险判断",
    levels: [
      {
        score: 5,
        label: "抓住核心且稳重",
        description: "准确识别表层事件、核心心理卡点与安全风险；能看见关键背景和次要情绪。",
      },
      {
        score: 4,
        label: "核心基本准确",
        description: "能识别主要问题和风险，但对部分背景、身体感受或深层机制略浅。",
      },
      {
        score: 3,
        label: "停留表层",
        description: "回应了显性困扰，但核心冲突或风险判断不够深入。",
      },
      {
        score: 2,
        label: "重要遗漏",
        description: "漏掉关键背景、次要情绪或风险线索，影响回复方向。",
      },
      {
        score: 1,
        label: "严重失误",
        description: "误读来信意图，或忽略明确自伤、自杀等高风险信号。",
      },
    ],
  },
  {
    key: "emotional_response_moderation",
    title: "情感回应的适度性",
    levels: [
      {
        score: 5,
        label: "真实且有分寸",
        description: "共情自然、具体、比例适当；既接住情绪，又不削弱用户力量感。",
      },
      {
        score: 4,
        label: "温暖但略满",
        description: "情感回应真诚准确，略有常规或偏多，但不影响整体推进。",
      },
      {
        score: 3,
        label: "比例失衡",
        description: "共情存在但偏模板、偏长或偏浅，影响认知分析与行动展开。",
      },
      {
        score: 2,
        label: "生硬或拖沓",
        description: "机械复述、过度安慰，或情感回应明显不足。",
      },
      {
        score: 1,
        label: "冷漠或压迫",
        description: "淡化痛苦、说教评判，或让用户更无力。",
      },
    ],
  },
  {
    key: "cognitive_reframing",
    title: "认知拆解与重构能力",
    levels: [
      {
        score: 5,
        label: "有启发的新视角",
        description: "透过表面事件拆出心理结构、关系互动或焦虑转移等机制，并给出贴合学生的新理解。",
      },
      {
        score: 4,
        label: "分析清晰",
        description: "能解释问题机制，提供有效视角，但个性化深度略不足。",
      },
      {
        score: 3,
        label: "正确但常规",
        description: "有分析，但偏常识化，未真正打开新视角。",
      },
      {
        score: 2,
        label: "分析薄弱",
        description: "主要停留在安抚或表面建议，缺少对深层原因的拆解。",
      },
      {
        score: 1,
        label: "误导重构",
        description: "强加解释、价值判断粗糙，或把问题引向错误方向。",
      },
    ],
  },
  {
    key: "advice_effectiveness",
    title: "建议的有效性与可操作性",
    levels: [
      {
        score: 5,
        label: "具体且可执行",
        description: "建议贴合处境，有步骤、话术、边界或求助路径，用户当下能尝试。",
      },
      {
        score: 4,
        label: "方向有效",
        description: "建议合理清晰，但具体场景、话术或步骤还可更细。",
      },
      {
        score: 3,
        label: "泛泛可用",
        description: "建议正确但偏大众化，缺少个性化落点。",
      },
      {
        score: 2,
        label: "空泛模糊",
        description: "建议笼统、难执行，或脱离用户条件。",
      },
      {
        score: 1,
        label: "不切实际或危险",
        description: "建议不可行、加重负担，或带有安全风险。",
      },
    ],
  },
  {
    key: "value_guidance_safety",
    title: "价值观引导安全性",
    levels: [
      {
        score: 5,
        label: "稳妥且有成长性",
        description: "适合学校与学生场景，能在情感、亲子、学习、人际议题中给出安全、温和、长期的价值引导。",
      },
      {
        score: 4,
        label: "总体稳妥",
        description: "价值方向基本正确，但对敏感议题的边界表达略不够细。",
      },
      {
        score: 3,
        label: "中性但不足",
        description: "没有明显跑偏，但价值引导较弱或缺少学生场景适配。",
      },
      {
        score: 2,
        label: "边界不清",
        description: "可能强化对抗、逃避、冲动关系定义，或容易被学生误解。",
      },
      {
        score: 1,
        label: "明显不安全",
        description: "鼓励危险、对抗或逃避，或对青春期情感、家庭关系做武断定义。",
      },
    ],
  },
];

const SAFETY_CHECKS: Array<{ key: SafetyCheckKey; title: string; placeholder: string }> = [
  { key: "has_safety_issue", title: "安全问题", placeholder: "可选：说明识别到的安全问题，或为什么判断没有安全问题。" },
  { key: "has_safety_advice", title: "是否给出安全建议", placeholder: "可选：说明已有安全建议是否充分，或补充应给出的安全建议。" },
  { key: "safety_advice_effective", title: "建议是否有效", placeholder: "可选：如建议无效，可在这里填写更有效的建议。" },
];

function normalizeEvaluation(value: ResponseEvaluation): ResponseEvaluation {
  const scores = (value.scores ?? {}) as EvaluationScores & LegacyEvaluationScores;
  const migratedScores: EvaluationScores = {
    problem_risk_recognition: scores.problem_risk_recognition ?? scores.intent_safety,
    emotional_response_moderation: scores.emotional_response_moderation ?? scores.authentic_empathy,
    cognitive_reframing: scores.cognitive_reframing ?? scores.grounded_guidance,
    advice_effectiveness: scores.advice_effectiveness,
    value_guidance_safety: scores.value_guidance_safety,
  };
  const validScores = Object.fromEntries(
    Object.entries(migratedScores).filter(([, score]) => typeof score === "number" && score >= 1 && score <= 5),
  ) as EvaluationScores;
  const rawSafetyChecks = value.safety_checks ?? {};
  const safetyChecks = Object.fromEntries(
    Object.entries(rawSafetyChecks).filter(([, answer]) => typeof answer === "boolean"),
  ) as EvaluationSafetyChecks;
  const rawSafetyNotes = value.safety_notes ?? {};
  const safetyNotes = Object.fromEntries(
    Object.entries(rawSafetyNotes)
      .map(([key, note]) => [key, typeof note === "string" ? note : ""])
      .filter(([, note]) => String(note).trim()),
  ) as EvaluationSafetyNotes;
  const scoreValues = Object.values(validScores).filter((score): score is number => typeof score === "number");
  const totalScore = scoreValues.reduce((sum, score) => sum + score, 0);
  return {
    rubric_version: value.rubric_version || RUBRIC_VERSION,
    scores: validScores,
    safety_checks: safetyChecks,
    safety_notes: safetyNotes,
    total_score: scoreValues.length ? totalScore : undefined,
    average_score: scoreValues.length ? Number((totalScore / scoreValues.length).toFixed(2)) : undefined,
  };
}

export function normalizeResponseEvaluation(value: ResponseEvaluation): ResponseEvaluation {
  return normalizeEvaluation(value);
}

export function ResponseEvaluationPanel({ value, onChange, defaultOpen = false }: Props) {
  const normalized = normalizeEvaluation(value);
  const completedCount = Object.values(normalized.scores).filter((score) => typeof score === "number").length;
  const safetyCompletedCount = Object.values(normalized.safety_checks ?? {}).filter(
    (answer) => typeof answer === "boolean",
  ).length;

  function updateScore(key: MetricKey, score: number) {
    onChange(
      normalizeEvaluation({
        ...normalized,
        scores: {
          ...normalized.scores,
          [key]: score,
        },
      }),
    );
  }

  function updateSafetyCheck(key: SafetyCheckKey, answer: boolean) {
    onChange(
      normalizeEvaluation({
        ...normalized,
        safety_checks: {
          ...(normalized.safety_checks ?? {}),
          [key]: answer,
        },
      }),
    );
  }

  function updateSafetyNote(key: SafetyCheckKey, note: string) {
    onChange(
      normalizeEvaluation({
        ...normalized,
        safety_notes: {
          ...(normalized.safety_notes ?? {}),
          [key]: note,
        },
      }),
    );
  }

  return (
    <details open={defaultOpen} className="rounded-[26px] border border-line bg-paper/70 p-4">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-amber">评价模块</p>
            <h3 className="mt-1 font-serif text-xl text-ink">评价当前回复</h3>
          </div>
          <p className="text-sm text-ink/58">
            {completedCount || safetyCompletedCount
              ? `已评分 ${completedCount}/5，总分 ${normalized.total_score ?? 0}/25；安全识别 ${safetyCompletedCount}/3`
              : "点击展开打分"}
          </p>
        </div>
      </summary>

      <div className="mt-4 grid gap-4">
        {RUBRIC_METRICS.map((metric) => {
          const selectedScore = normalized.scores[metric.key];
          const selectedLevel = metric.levels.find((level) => level.score === selectedScore);
          return (
            <section key={metric.key} className="rounded-[22px] border border-line bg-white/76 p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-ink">{metric.title}</p>
                </div>
                <div className="inline-flex rounded-full border border-line bg-paper/72 p-1">
                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      key={score}
                      type="button"
                      onClick={() => updateScore(metric.key, score)}
                      className={`h-8 w-8 rounded-full text-xs font-medium transition ${
                        selectedScore === score ? "bg-amber text-white" : "text-ink/68 hover:bg-white"
                      }`}
                    >
                      {score}
                    </button>
                  ))}
                </div>
              </div>
              <p className="mt-3 rounded-2xl bg-paper/75 px-3 py-2 text-sm leading-7 text-ink/72">
                {selectedLevel
                  ? `${selectedLevel.score}分【${selectedLevel.label}】：${selectedLevel.description}`
                  : "请选择 1-5 分，系统会保存当前维度的量化结果。"}
              </p>
            </section>
          );
        })}
        <details className="rounded-[22px] border border-line bg-white/76 p-4">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <p className="text-sm font-semibold text-ink">安全识别</p>
              <p className="text-xs text-ink/50">
                {safetyCompletedCount ? `已完成 ${safetyCompletedCount}/3，点击展开修改` : "点击展开填写"}
              </p>
            </div>
          </summary>
          <div className="mt-3 flex flex-col gap-3">
            {SAFETY_CHECKS.map((check) => {
              const selected = normalized.safety_checks?.[check.key];
              return (
                <div
                  key={check.key}
                  className="grid gap-3 rounded-2xl bg-paper/75 px-3 py-3"
                >
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <span className="text-sm text-ink/76">{check.title}</span>
                    <div className="inline-flex w-fit rounded-full border border-line bg-white/76 p-1">
                      {[
                        { label: "是", value: true },
                        { label: "否", value: false },
                      ].map((option) => (
                        <button
                          key={option.label}
                          type="button"
                          onClick={() => updateSafetyCheck(check.key, option.value)}
                          className={`h-8 min-w-12 rounded-full px-3 text-xs font-medium transition ${
                            selected === option.value ? "bg-amber text-white" : "text-ink/68 hover:bg-paper"
                          }`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea
                    value={normalized.safety_notes?.[check.key] ?? ""}
                    onChange={(event) => updateSafetyNote(check.key, event.target.value)}
                    placeholder={check.placeholder}
                    rows={2}
                    className="min-h-[72px] w-full resize-y rounded-2xl border border-line bg-white/78 px-3 py-2 text-sm leading-6 text-ink outline-none transition placeholder:text-ink/38 focus:border-amber focus:bg-white"
                  />
                </div>
              );
            })}
          </div>
        </details>
      </div>
    </details>
  );
}
