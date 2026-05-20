const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? "";

function normalizeBaseUrl(value: string): string {
  if (!value) {
    return "";
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export const API_BASE_URL = normalizeBaseUrl(rawApiBaseUrl);

export function buildApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}
