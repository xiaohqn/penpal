import { request } from "../../lib/request";
import { streamPost } from "../../lib/sse";
import type { SourceAnnotation } from "../records/types";
import type { DraftCandidate, PersonaCatalogResponse, PlannerOutput } from "./types";

export async function fetchPersonaCatalog() {
  return request<PersonaCatalogResponse>("/personas");
}

export async function streamGenerations(
  payload: { user_input: string; persona_names: string[]; compare_sources?: boolean; source_mode?: string; use_deep_thinking?: boolean },
  onEvent: (eventName: string, data: any) => void,
) {
  return streamPost("/api/v1/generations/stream", payload, onEvent);
}

export function generateFromPlan(payload: {
  user_input: string;
  persona_name: string;
  planner_output: PlannerOutput;
  source_mode?: string;
  use_deep_thinking?: boolean;
}) {
  return request<DraftCandidate>("/generations/from-plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rewriteAnnotations(payload: {
  current_response: string;
  annotations: SourceAnnotation[];
  expert_annotation: string;
  persona_name: string;
  source_mode?: string;
  use_deep_thinking?: boolean;
}) {
  return request<{ revisions: Array<{ id: string; revised_text: string }>; raw?: string }>("/generations/rewrite-annotations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
