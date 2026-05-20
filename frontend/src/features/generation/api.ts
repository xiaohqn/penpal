import { request } from "../../lib/request";
import { streamPost } from "../../lib/sse";
import type { PersonaCatalogResponse } from "./types";

export async function fetchPersonaCatalog() {
  return request<PersonaCatalogResponse>("/personas");
}

export async function streamGenerations(
  payload: { user_input: string; persona_names: string[]; compare_sources?: boolean; source_mode?: string },
  onEvent: (eventName: string, data: any) => void,
) {
  return streamPost("/api/v1/generations/stream", payload, onEvent);
}
