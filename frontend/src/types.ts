export type APIResponse<T> = {
  detail: string;
  data: T;
  extra: Record<string, unknown>;
};

export type APIPaginatedResponse<T> = {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
  data: T[];
};

export type Message = {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type Conversation = {
  id: number;
  last_message: Message | null;
  created_at: string;
  updated_at: string;
};
