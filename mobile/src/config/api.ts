import axios from "axios";
import * as SecureStore from "expo-secure-store";

// ─── Base URL ─────────────────────────────────────────────────────────────────
// Development  → your local machine (update IP if testing on a physical device)
// Production   → your Railway deployment URL (set EXPO_PUBLIC_API_URL in .env)

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api";

// ─── Axios instance ───────────────────────────────────────────────────────────

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ─── Auth interceptor — attach JWT on every request ──────────────────────────

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync("access_token");
  if (token) {
    config.headers.Authorization = Bearer ${token};
  }
  return config;
});

// ─── Response interceptor — refresh token on 401 ─────────────────────────────

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = await SecureStore.getItemAsync("refresh_token");
        const { data } = await axios.post(${API_BASE_URL}/auth/token/refresh/, {
          refresh,
        });
        await SecureStore.setItemAsync("access_token", data.access);
        original.headers.Authorization = Bearer ${data.access};
        return api(original);
      } catch {
        // Refresh failed — clear tokens, caller should redirect to login
        await SecureStore.deleteItemAsync("access_token");
        await SecureStore.deleteItemAsync("refresh_token");
      }
    }
    return Promise.reject(error);
  }
);