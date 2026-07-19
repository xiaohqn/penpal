import type { DraftState, PlannerOutput } from "../generation/types";
import type { ResponseEvaluation, ResponseVersion, SourceAnnotation } from "../records/types";

export type WorkspaceTaskMode = "single" | "excel_batch" | "mail_batch" | "manual";
export type WorkspaceTaskStatus = "draft" | "in_progress" | "completed" | "archived";

export type WorkspaceTaskState = {
  userInput?: string;
  selectedPersonas?: string[];
  selectedPersona?: string | null;
  drafts?: DraftState[];
  polishedText?: string;
  expertAnnotation?: string;
  sourceAnnotations?: SourceAnnotation[];
  responseVersions?: ResponseVersion[];
  responseEvaluation?: ResponseEvaluation;
  activeVersionIndex?: number;
  initialAiResponse?: string;
  initialPlannerOutput?: PlannerOutput | null;
  finalizationMode?: string;
  plannerOutput?: PlannerOutput;
  useDeepThinking?: boolean;
  activeRightTab?: string;
};

export type WorkspaceTask = {
  id: number;
  counselor_id: string;
  mode: WorkspaceTaskMode;
  status: WorkspaceTaskStatus;
  title: string;
  summary: string;
  state_json: WorkspaceTaskState;
  batch_session_id?: number | null;
  created_at: string;
  updated_at: string;
};

export type WorkspaceTaskListResponse = {
  items: WorkspaceTask[];
  total: number;
};

export type WorkspaceTaskSavePayload = {
  mode: WorkspaceTaskMode;
  status: WorkspaceTaskStatus;
  title?: string;
  summary?: string;
  state: WorkspaceTaskState;
  batch_session_id?: number | null;
};
