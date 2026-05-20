export type PlannerOutput = {
  intent_analysis?: string;
  risk_assessment?: string;
  persona_strategy?: string;
  paragraph_plan?: string[];
  must_include?: string[];
  must_avoid?: string[];
  generation_plan?: string;
  style_summary?: Record<string, string>;
};

export type DraftCandidate = {
  draft_id: string;
  persona_name: string;
  source: string;
  source_label: string;
  style_config: Record<string, string>;
  planner_output: PlannerOutput;
  response: string;
  raw_response?: string;
};

export type PersonaCatalogItem = {
  name: string;
  blurb: string;
  style_config: Record<string, string>;
  raw_config: Record<string, string>;
};

export type PersonaCatalogResponse = {
  personas: PersonaCatalogItem[];
  style_axes: Record<string, Record<string, string>>;
};

export type DraftState = DraftCandidate & {
  status: "idle" | "streaming" | "done" | "error";
  error?: string;
};
