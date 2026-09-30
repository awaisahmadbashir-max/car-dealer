import apiClient from "./apiClient";

export type LoginResult = {
  access_token: string;
  token_type: string;
};

type LoginApiEnvelope = {
  detail?: string;
  data: LoginResult & Record<string, unknown>;
};

export type RegisterPayload = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
};

export const authAPI = {
  login: async (email: string, password: string): Promise<LoginResult> => {
    const response = await apiClient.post<LoginApiEnvelope>("/auth/login", {
      email,
      password,
    });
    const payload = response.data.data;
    return {
      access_token: payload.access_token,
      token_type: payload.token_type,
    };
  },

  register: async (payload: RegisterPayload): Promise<void> => {
    await apiClient.post("/auth/register", payload);
  },
};
