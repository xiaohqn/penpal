import { buildApiUrl } from "./api-base";

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
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new RequestError(message || "Request failed", response.status);
  }

  return response.json() as Promise<T>;
}
