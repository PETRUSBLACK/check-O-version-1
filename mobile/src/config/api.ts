import axios, { AxiosError } from "axios";
import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

// ─── Base URL ─────────────────────────────────────────────────────────────────
// In development you normally need nothing: the phone already reached this laptop
// to load the app, so Expo knows its address and we reuse it. That means a change
// of Wi-Fi or hotspot — which changes the laptop's IP — fixes itself.
//
// Set EXPO_PUBLIC_API_URL in mobile/.env only to point somewhere else:
//   Railway → https://<your-app>.up.railway.app/api
// A value set there always wins, so remember to clear it when you go back to
// running the backend on this laptop.

/** The laptop address Expo served this app from, e.g. "10.197.207.129". */
function devServerHost(): string | null {
  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as { platform?: { hostUri?: string } }).platform?.hostUri;
  if (!hostUri) return null;
  // hostUri looks like "10.197.207.129:8081" or "10.197.207.129:8081/path"
  const host = hostUri.split("/")[0].split(":")[0];
  if (!host || host === "localhost" || host === "127.0.0.1") return null;
  return host;
}

function resolveBaseUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (explicit) return explicit;

  const host = devServerHost();
  if (host) return `http://${host}:8000/api`;

  // Web preview, or a built app with nothing configured.
  return "http://localhost:8000/api";
}

export const API_BASE_URL = resolveBaseUrl();

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
    // In development the cause is almost never the phone's internet — it's the
    // backend not running, or running without `0.0.0.0`. Say which address failed
    // so the next thing to check is obvious.
    if (__DEV__) {
      return `Can't reach the backend at ${API_BASE_URL}. Is it running with "python manage.py runserver 0.0.0.0:8000"?`;
    }
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
