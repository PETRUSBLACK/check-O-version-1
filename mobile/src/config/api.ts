import axios, { AxiosError } from "axios";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

// ─── Base URL ─────────────────────────────────────────────────────────────────
// Set EXPO_PUBLIC_API_URL in mobile/.env:
//   Laptop on the same Wi-Fi → http://<your-laptop-IP>:8000/api
//   Railway                  → https://<your-app>.up.railway.app/api
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api";

const ACCESS = "access_token";
const REFRESH = "refresh_token";

// Phones keep tokens in the encrypted SecureStore. SecureStore doesn't exist in
// a web browser, so the web preview falls back to localStorage.
const store =
  Platform.OS === "web"
    ? {
        get: async (k: string) => globalThis.localStorage?.getItem(k) ?? null,
        set: async (k: string, v: string) => globalThis.localStorage?.setItem(k, v),
        del: async (k: string) => globalThis.localStorage?.removeItem(k),
      }
    : {
        get: (k: string) => SecureStore.getItemAsync(k),
        set: (k: string, v: string) => SecureStore.setItemAsync(k, v),
        del: (k: string) => SecureStore.deleteItemAsync(k),
      };

export const tokens = {
  getAccess: () => store.get(ACCESS),
  getRefresh: () => store.get(REFRESH),
  async save(access: string, refresh?: string) {
    await store.set(ACCESS, access);
    if (refresh) await store.set(REFRESH, refresh);
  },
  async clear() {
    await store.del(ACCESS);
    await store.del(REFRESH);
  },
};

// Called when the session can't be refreshed, so the app returns to sign-in.
let onSessionExpired: (() => void) | null = null;
export const setOnSessionExpired = (fn: () => void) => {
  onSessionExpired = fn;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Attach the JWT to every request
api.interceptors.request.use(async (config) => {
  const token = await tokens.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, try the refresh token once
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      const refresh = await tokens.getRefresh();
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, { refresh });
          await tokens.save(data.access, data.refresh);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          // fall through
        }
      }
      await tokens.clear();
      onSessionExpired?.();
    }
    return Promise.reject(error);
  },
);

/** Turn an API error into one readable sentence for the user. */
export function errorMessage(err: unknown, fallback = "Something went wrong. Please try again."): string {
  const e = err as AxiosError<any>;
  if (!e?.response) {
    return "Can't reach Check-O. Check your internet connection.";
  }
  const data = e.response.data;
  if (typeof data === "string") return fallback;
  if (data?.detail) return String(data.detail);
  if (data && typeof data === "object") {
    const first = Object.values(data)[0];
    if (Array.isArray(first) && first.length) return String(first[0]);
    if (typeof first === "string") return first;
  }
  return fallback;
}
