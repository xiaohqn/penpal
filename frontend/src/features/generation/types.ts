export type PlannerOutput = {
  intention?: string;
  intent_analysis?: string;
  surface_issue?: string;
  core_issue?: string;
  positive_motive?: string;
  wrong_but_easy_answer?: string;
  risk_assessment?: string;
  value_guidance?: string;
  persona_strategy?: string;
  response_focus?: string;
  action_strategy?: string[];
  sample_words?: string[];
  must_include?: string[];
  must_avoid?: string[];
  generation_plan?: string;
  rag_references?: RagReference[];
  style_summary?: Record<string, string>;
};

export type RagReference = {
  record_id?: number;
  source?: string;
  score?: number;
  selected_persona_name?: string;
  sample_tags?: Record<string, unknown>;
  planner_labels?: Record<string, unknown>;
  user_input_excerpt?: string;
  expert_response_excerpt?: string;
  expert_annotation?: string;
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
  safety_review?: SafetyReview;
};

export type SafetyReview = {
  risk_level?: string;
  confidence?: number;
  categories?: string[];
  signals?: string[];
  reasoning?: string;
  blocked?: boolean;
  replacement_used?: boolean;
  original_response?: string;
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
