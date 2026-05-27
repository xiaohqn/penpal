/**
 * 输入：
 * - 安全检测请求参数，或安全回复批注重生成请求参数。
 * 输出：
 * - 返回后端 `/safety/check` 和 `/safety/regenerate` 接口的结构化响应。
 * 作用：
 * - 集中封装前端对安全检测与安全回复批注重生成接口的访问。
 */
import { buildApiUrl } from "../../lib/api-base";
import { RequestError } from "../../lib/request";
import type {
  SafetyCheckRequest,
  SafetyCheckResponse,
  SafetyRegenerateRequest,
  SafetyResponseCandidate,
} from "./types";

async function parseSafetyError(response: Response, fallbackMessage: string) {
  /**
   * 输入：
   * - response：后端返回的失败响应对象。
   * - fallbackMessage：当响应体为空或无法解析时使用的兜底提示。
   * 输出：
   * - 抛出包含更友好错误文案的 `RequestError`。
   * 作用：
   * - 统一处理安全链路接口的失败响应，避免检测与重生成各自重复维护一套错误解析逻辑。
   */

  const rawMessage = await response.text();
  let message = rawMessage || fallbackMessage;
  try {
    const parsed = JSON.parse(rawMessage) as { detail?: string };
    if (parsed.detail) {
      message = parsed.detail;
    }
  } catch {
    // 保持原始文本错误信息。
  }
  throw new RequestError(message, response.status);
}

export async function checkSafety(payload: SafetyCheckRequest) {
  /**
   * 输入：
   * - payload：安全检测请求参数，包含原始来信与当前来源模式。
   * 输出：
   * - 返回后端 `/safety/check` 接口的结构化检测结果。
   * 作用：
   * - 为工作台顶部的“安全检测”按钮提供统一请求入口。
   */

  const response = await fetch(buildApiUrl("/api/v1/safety/check"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseSafetyError(response, "风险检测失败");
  }

  return response.json() as Promise<SafetyCheckResponse>;
}

export async function regenerateSafetyReply(payload: SafetyRegenerateRequest) {
  /**
   * 输入：
   * - payload：安全回复批注重生成请求参数，包含当前回复、划词批注和专家总体说明。
   * 输出：
   * - 返回后端 `/safety/regenerate` 接口生成的新安全回复候选。
   * 作用：
   * - 为安全回复页新增的“按批注重生成”按钮提供统一请求入口。
   */

  const response = await fetch(buildApiUrl("/api/v1/safety/regenerate"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseSafetyError(response, "安全回复重生成失败");
  }

  return response.json() as Promise<SafetyResponseCandidate>;
}
