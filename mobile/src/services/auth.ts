import { api, tokens } from "../config/api";

// Mirrors the backend: apps/users (UserSerializer, RegisterSerializer)

export type UserRole = "customer" | "vendor" | "admin";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  date_joined: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role?: "customer" | "vendor";
}

export const authService = {
  // POST /api/auth/register/
  async register(payload: RegisterPayload): Promise<User> {
    const { data } = await api.post<User>("/auth/register/", payload);
    return data;
  },

  // POST /api/auth/token/  → saves the tokens
  async login(email: string, password: string): Promise<void> {
    const { data } = await api.post<{ access: string; refresh: string }>("/auth/token/", {
      email: email.trim().toLowerCase(),
      password,
    });
    await tokens.save(data.access, data.refresh);
  },

  // GET /api/auth/me/
  async me(): Promise<User> {
    const { data } = await api.get<User>("/auth/me/");
    return data;
  },

  // POST /api/auth/logout/ (blacklists the refresh token), then forget tokens
  async logout(): Promise<void> {
    const refresh = await tokens.getRefresh();
    try {
      if (refresh) await api.post("/auth/logout/", { refresh });
    } finally {
      await tokens.clear();
    }
  },

  // POST /api/auth/password/reset/
  async requestPasswordReset(email: string): Promise<void> {
    await api.post("/auth/password/reset/", { email: email.trim().toLowerCase() });
  },
};
