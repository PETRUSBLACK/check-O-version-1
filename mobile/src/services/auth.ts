import * as SecureStore from "expo-secure-store";
import { api } from "../config/api";

// ─── Types ────────────────────────────────────────────────────────────────────

export type UserRole = "customer" | "vendor" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

// ─── Auth service — mirrors POST /api/auth/* endpoints ───────────────────────

export const authService = {
  async register(payload: {
    email: string;
    password: string;
    full_name: string;
    role: UserRole;
  }): Promise<User> {
    const { data } = await api.post("/auth/register/", payload);
    return data;
  },

  async login(email: string, password: string): Promise<AuthTokens> {
    const { data } = await api.post<AuthTokens>("/auth/token/", {
      email,
      password,
    });
    await SecureStore.setItemAsync("access_token", data.access);
    await SecureStore.setItemAsync("refresh_token", data.refresh);
    return data;
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>("/auth/me/");
    return data;
  },

  async logout(refreshToken: string): Promise<void> {
    await api.post("/auth/logout/", { refresh: refreshToken });
    await SecureStore.deleteItemAsync("access_token");
    await SecureStore.deleteItemAsync("refresh_token");
  },

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await api.post("/auth/password/change/", {
      old_password: oldPassword,
      new_password: newPassword,
    });
  },

  async requestPasswordReset(email: string): Promise<void> {
    await api.post("/auth/password/reset/", { email });
  },
};