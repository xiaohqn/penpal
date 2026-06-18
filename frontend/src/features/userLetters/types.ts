export type UserLetter = {
  id: number;
  user_id: string;
  signature: string;
  letter_text: string;
  reply_text: string;
  reply_source: string;
  status: string;
  response_preference: string;
  assigned_counselor_id: string | null;
  created_at: string;
  updated_at: string;
};

export type UserLetterListResponse = {
  items: UserLetter[];
  total: number;
};

export type CreateUserLetterPayload = {
  signature: string;
  letter_text: string;
  reply_text: string;
  reply_source?: string;
  status?: string;
  response_preference?: string;
};
