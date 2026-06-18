import { buildApiUrl } from "./api-base";
import { getAuthHeaders, getStoredCounselorId, getStoredUserId } from "../app/auth";

export type StreamEventHandler = (eventName: string, payload: unknown) => void;

export async function streamPost(
  path: string,
  body: unknown,
  onEvent: StreamEventHandler,
): Promise<void> {
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "X-Counselor-Id": getStoredCounselorId(),
      "X-User-Id": getStoredUserId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const lines = part.split("\n");
      let eventName = "message";
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        }
        if (line.startsWith("data:")) {
          data += line.slice(5).trim();
        }
      }

      if (!data) {
        continue;
      }

      onEvent(eventName, JSON.parse(data));
    }
  }
}
