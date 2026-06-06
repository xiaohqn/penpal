export type EvaluationScores = {
  intent_safety?: number;
  authentic_empathy?: number;
  grounded_guidance?: number;
  narrative_companionship?: number;
};

export type ResponseEvaluation = {
  rubric_version: string;
  scores: EvaluationScores;
  total_score?: number;
  average_score?: number;
};

export type RecordItem = {
  id: number;
  user_input: string;
  selected_persona_name: string;
  expert_annotation: string;
  rag_ready: string;
  sample_reason: string;
  created_at: string;
  updated_at: string;
};

export type RecordListResponse = {
  items: RecordItem[];
  total: number;
  page: number;
  page_size: number;
};

export type RecordDetail = {
  id: number;
  user_input: string;
  selected_persona_name: string;
  selected_style_config_json: Record<string, string>;
  planner_output_json: Record<string, unknown>;
  draft_candidates_json: Array<Record<string, unknown>>;
  ai_selected_raw_response: string;
  expert_polished_response: string;
  expert_annotation: string;
  rag_ready: string;
  sample_reason: string;
  sample_tags_json: Record<string, unknown>;
  planner_labels_json: Record<string, unknown>;
  evaluation_json: ResponseEvaluation | Record<string, unknown>;
  sample_snapshot_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SaveRecordPayload = {
  user_input: string;
  selected_persona_name: string;
  selected_style_config: Record<string, unknown>;
  planner_output: Record<string, unknown>;
  draft_candidates: Array<Record<string, unknown>>;
  ai_selected_raw_response: string;
  expert_polished_response: string;
  expert_annotation: string;
  rag_ready?: string;
  sample_reason?: string;
  sample_snapshot?: Record<string, unknown>;
  evaluation?: ResponseEvaluation;
  source_annotations?: SourceAnnotation[];
  response_versions?: ResponseVersion[];
  batch_session_id?: number | null;
  batch_item_id?: number | null;
};

export type BatchExcelItem = {
  id?: number;
  session_id?: number;
  row_number: number;
  user_input: string;
  selected_persona_names: string[];
  selected_persona_name?: string;
  selected_style_config_json?: Record<string, unknown>;
  planner_output_json?: Record<string, unknown>;
  draft_candidates_json?: Array<Record<string, unknown>>;
  ai_selected_raw_response?: string;
  latest_response?: string;
  expert_annotation?: string;
  source_annotations_json?: SourceAnnotation[];
  response_versions_json?: ResponseVersion[];
  sample_tags_json?: Record<string, unknown>;
  planner_labels_json?: Record<string, unknown>;
  evaluation_json?: ResponseEvaluation | Record<string, unknown>;
  active_version_index?: number;
  status?: string;
  record_id?: number | null;
};

export type BatchExcelImportResponse = {
  items: BatchExcelItem[];
  total: number;
};

export type ReviewedBatchItem = {
  item_id?: number;
  row_number: number;
  user_input: string;
  selected_persona_name: string;
  final_response: string;
  expert_annotation: string;
  rag_ready?: string;
  sample_reason?: string;
  source_annotations?: SourceAnnotation[];
  evaluation?: ResponseEvaluation;
  active_version_index?: number;
};

export type SourceAnnotation = {
  id: string;
  start: number;
  end: number;
  quote: string;
  note: string;
  color: string;
};

export type ResponseVersion = {
  version_index: number;
  label: string;
  response: string;
  selected_persona_name: string;
  created_at: string;
  source: string;
  source_annotations: SourceAnnotation[];
};

export type BatchSessionItem = {
  id: number;
  session_id: number;
  row_number: number;
  user_input: string;
  status: string;
  selected_persona_names_json: string[];
  selected_persona_name: string;
  selected_style_config_json: Record<string, unknown>;
  planner_output_json: Record<string, unknown>;
  draft_candidates_json: Array<Record<string, unknown>>;
  ai_selected_raw_response: string;
  latest_response: string;
  expert_annotation: string;
  rag_ready: string;
  sample_reason: string;
  sample_snapshot_json: Record<string, unknown>;
  source_annotations_json: SourceAnnotation[];
  response_versions_json: ResponseVersion[];
  sample_tags_json: Record<string, unknown>;
  planner_labels_json: Record<string, unknown>;
  evaluation_json: ResponseEvaluation | Record<string, unknown>;
  active_version_index: number;
  record_id: number | null;
  created_at: string;
  updated_at: string;
};

export type BatchSessionDetail = {
  id: number;
  title: string;
  source_file_name: string;
  status: string;
  total_items: number;
  completed_items: number;
  current_item_id: number | null;
  created_at: string;
  updated_at: string;
  items: BatchSessionItem[];
};

export type BatchSessionListItem = {
  id: number;
  title: string;
  source_file_name: string;
  status: string;
  total_items: number;
  completed_items: number;
  current_item_id: number | null;
  created_at: string;
  updated_at: string;
};

export type BatchSessionListResponse = {
  items: BatchSessionListItem[];
  total: number;
};

export type BatchSessionItemUpdatePayload = {
  selected_persona_names: string[];
  selected_persona_name: string;
  selected_style_config: Record<string, unknown>;
  planner_output: Record<string, unknown>;
  draft_candidates: Array<Record<string, unknown>>;
  ai_selected_raw_response: string;
  latest_response: string;
  expert_annotation: string;
  rag_ready: string;
  sample_reason: string;
  sample_tags: Record<string, unknown>;
  planner_labels: Record<string, unknown>;
  evaluation: ResponseEvaluation;
  sample_snapshot: Record<string, unknown>;
  source_annotations: SourceAnnotation[];
  response_versions: ResponseVersion[];
  active_version_index: number;
  status: string;
  record_id?: number | null;
};

export type BatchSessionItemRegeneratePayload = {
  selected_persona_name: string;
  selected_persona_names: string[];
  source_annotations: SourceAnnotation[];
  expert_annotation: string;
  current_response: string;
  planner_output?: Record<string, unknown>;
};
