import { request } from "../../lib/request";
import { streamPost } from "../../lib/sse";
import type { DraftCandidate, PersonaCatalogResponse, PlannerOutput } from "./types";

export async function fetchPersonaCatalog() {
  return request<PersonaCatalogResponse>("/personas");
}

export async function streamGenerations(
  payload: { user_input: string; persona_names: string[]; compare_sources?: boolean; source_mode?: string },
  onEvent: (eventName: string, data: any) => void,
) {
  return streamPost("/api/v1/generations/stream", payload, onEvent);
}

export function generateFromPlan(payload: {
  user_input: string;
  persona_name: string;
  planner_output: PlannerOutput;
  source_mode?: string;
}) {
  return request<DraftCandidate>("/generations/from-plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
