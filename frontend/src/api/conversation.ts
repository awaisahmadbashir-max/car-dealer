import type {
  APIPaginatedResponse,
  APIResponse,
  Conversation,
  Message,
} from "../types";
import apiClient from "./apiClient";

export const conversationAPI = {
  getConversations: async (params: {
    page: number;
    limit: number;
  }): Promise<APIPaginatedResponse<Conversation>> => {
    const response = await apiClient.get("/conversation/", { params });
    return response.data;
  },
  getMessages: async (params: {
    page: number;
    limit: number;
    conversation_id: number;
  }): Promise<APIPaginatedResponse<Message>> => {
    const response = await apiClient.get(
      `/conversation/${params.conversation_id}/message`,
      { params: { page: params.page, limit: params.limit } },
    );
    return response.data;
  },
  createMessage: async (params: {
    content: string;
    conversation_id?: number;
  }): Promise<APIResponse<Message>> => {
    const response = await apiClient.post(`/conversation/message`, {
      content: params.content,
      ...(params.conversation_id && {
        conversation_id: params.conversation_id,
      }),
    });
    return response.data;
  },
};
