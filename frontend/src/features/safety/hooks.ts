/**
 * 输入：
 * - 安全检测请求参数、批注重生成请求参数，以及可选的初始安全检测状态。
 * - `checkSafety` 和 `regenerateSafetyReply` 接口返回的结果或错误。
 * 输出：
 * - 提供安全检测状态、批注重生成 mutation、重置方法和加载态。
 * 作用：
 * - 统一管理安全检测与安全回复批注重生成请求的生命周期，让页面层只关注交互编排。
 */
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { checkSafety, regenerateSafetyReply } from "./api";
import type {
  SafetyCheckResponse,
  SafetyRegenerateRequest,
  SafetyResponseCandidate,
  SafetyState,
} from "./types";

const defaultSafetyState: SafetyState = {
  status: "idle",
  result: null,
  error: null,
};

export function useSafetyCheck(initialState: SafetyState = defaultSafetyState) {
  const [state, setState] = useState<SafetyState>(initialState);

  const mutation = useMutation({
    mutationFn: checkSafety,
    onMutate: () => {
      setState({
        status: "loading",
        result: null,
        error: null,
      });
    },
    onSuccess: (result: SafetyCheckResponse) => {
      setState({
        status: "success",
        result,
        error: null,
      });
    },
    onError: (error) => {
      setState({
        status: "error",
        result: null,
        error: error instanceof Error ? error.message : "风险检测失败",
      });
    },
  });

  return {
    state,
    runSafetyCheck: mutation.mutateAsync,
    resetSafetyState: () => setState(defaultSafetyState),
    replaceSafetyResult: (result: SafetyCheckResponse) =>
      setState({
        status: "success",
        result,
        error: null,
      }),
    isChecking: mutation.isPending,
  };
}

export function useRegenerateSafetyReply() {
  /**
   * 输入：
   * - 安全回复批注重生成请求参数。
   * 输出：
   * - 返回一个 React Query mutation，用于触发安全回复重生成并暴露加载态。
   * 作用：
   * - 把安全页的“按批注重生成”请求生命周期集中到 hook 中，保持与其它数据动作的一致用法。
   */

  return useMutation<SafetyResponseCandidate, Error, SafetyRegenerateRequest>({
    mutationFn: (payload) => regenerateSafetyReply(payload),
  });
}
