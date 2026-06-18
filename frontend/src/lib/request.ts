import { buildApiUrl } from "./api-base";
import { getAuthHeaders, getStoredCounselorId, getStoredUserId } from "../app/auth";

const API_PREFIX = "/api/v1";

export class RequestError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(`${API_PREFIX}${path}`), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Counselor-Id": getStoredCounselorId(),
      "X-User-Id": getStoredUserId(),
      ...getAuthHeaders(),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new RequestError(message || "Request failed", response.status);
  }

  return response.json() as Promise<T>;
}
