/**
 * 输入：
 * - canCheck / isChecking：控制风险检测按钮是否可用，以及是否展示进行中状态。
 * - onCheck：触发一次新的风险检测请求。
 * - statusText / errorText：最近一次检测后的提示信息或错误信息；在紧凑按钮模式下会优先保持界面简洁，
 *   但一旦出现错误或结果提示，就会在按钮下方补右对齐的多行文字说明，避免向左挤压标题区域。
 * - variant：控制风险检测入口是以独立卡片展示，还是以内联紧凑块展示在其它面板右侧。
 * 输出：
 * - 渲染风险检测操作区。
 * 作用：
 * - 这个组件承载工作台里的安全检测入口，只负责发起检测和反馈结果，
 *   具体摆放位置与视觉密度由页面通过 `variant` 决定。
 */
import { ShieldAlert } from "lucide-react";

type Props = {
  canCheck: boolean;
  isChecking: boolean;
  onCheck: () => void;
  statusText?: string | null;
  errorText?: string | null;
  variant?: "card" | "inline";
};

export function SafetyCheckBar({
  canCheck,
  isChecking,
  onCheck,
  statusText,
  errorText,
  variant = "card",
}: Props) {
  if (variant === "inline") {
    const inlineHint = errorText || statusText || "风险代码检测";
    const inlineButtonLabel = isChecking ? "检测中..." : "风险检测代码";
    const inlineFeedbackText = errorText || statusText || null;

    return (
      <div className="flex w-full max-w-[170px] flex-col items-end gap-2 xl:w-[170px]">
        <button
          type="button"
          onClick={onCheck}
          disabled={!canCheck || isChecking}
          title={inlineHint}
          aria-label={`${inlineButtonLabel}。${inlineHint}`}
          className={`inline-flex h-12 items-center justify-center gap-2 rounded-full border px-4 text-sm shadow-soft backdrop-blur transition ${
            errorText
              ? "border-red-300 bg-red-50 text-red-600 hover:bg-red-100"
              : statusText
                ? "border-moss/30 bg-moss/10 text-moss hover:bg-moss/15"
                : "border-line bg-white/78 text-moss hover:bg-paper/92"
          } disabled:cursor-not-allowed disabled:opacity-45`}
        >
          <ShieldAlert size={20} className={isChecking ? "animate-pulse" : ""} />
          <span>{inlineButtonLabel}</span>
        </button>
        {inlineFeedbackText ? (
          <p
            className={`pl-1 text-xs leading-5 ${
              errorText ? "text-red-600" : "text-moss"
            } w-full whitespace-normal break-words text-left`}
          >
            {inlineFeedbackText}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <section className="rounded-panel border border-line bg-white/75 p-6 shadow-soft backdrop-blur">
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-moss">风险检测</p>
          <h2 className="mt-1 font-serif text-2xl text-ink">先看这封来信是否需要安全回复兜底</h2>
          <p className="mt-2 text-sm leading-6 text-ink/68">
            点击后会返回风险类型判断；如果存在明显风险，中间区域会切换为安全回复结果页。
          </p>
        </div>
        {statusText ? <p className="text-sm text-moss">{statusText}</p> : null}
        {errorText ? <p className="text-sm text-red-600">{errorText}</p> : null}
        <div>
          <button
            type="button"
            onClick={onCheck}
            disabled={!canCheck || isChecking}
            className="rounded-full bg-moss px-5 py-3 text-sm text-white transition disabled:cursor-not-allowed disabled:bg-moss/40"
          >
            {isChecking ? "检测中..." : "风险代码检测"}
          </button>
        </div>
      </div>
    </section>
  );
}
