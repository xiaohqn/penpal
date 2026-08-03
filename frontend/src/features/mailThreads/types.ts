export type ReplyMode = "ai" | "human";

export type ResponsePreference = "温柔陪伴" | "理性分析" | "启发引导";

export type MailMessage = {
  id: number;
  thread_id: number;
  sender_type: "user" | "ai" | "counselor";
  sender_id: string;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ConversationMemory = {
  id: number;
  thread_id: number;
  user_id: string;
  summary: string;
  message_count: number;
  updated_at: string;
};

export type RiskLevel = "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRISIS";

export type RiskAssessment = {
  id: number;
  user_id: string;
  thread_id: number;
  message_id: number | null;
  target_type: string;
  risk_level: RiskLevel;
  confidence: number;
  categories: string[];
  signals: string[];
  reasoning: string;
  uncertainties: string[];
  avoid_in_reply: string[];
  protective_suggestions: string[];
  handoff: "none" | "review" | "priority" | "urgent";
  reviewed: boolean;
  created_at: string;
};

export type MailThread = {
  id: number;
  user_id: string;
  signature: string;
  title: string;
  reply_mode: ReplyMode;
  response_preference: ResponsePreference;
  status: string;
  assigned_counselor_id: string | null;
  created_at: string;
  updated_at: string;
  messages: MailMessage[];
  memory: ConversationMemory | null;
  risk_assessments: RiskAssessment[];
};

export type MailThreadListResponse = {
  items: MailThread[];
  total: number;
};

export type MailThreadArchiveResponse = {
  record_id: number;
  rag_ready: string;
};

export type CreateMailThreadPayload = {
  signature: string;
  content: string;
  reply_mode: ReplyMode;
  response_preference: ResponsePreference;
  ai_reply_text?: string;
};

export type CreateMailMessagePayload = {
  content: string;
  ai_reply_text?: string;
};
