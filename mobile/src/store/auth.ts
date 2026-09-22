import { create } from "zustand";

import { setOnSessionExpired, tokens } from "../config/api";
import { authService, RegisterPayload, User } from "../services/auth";

type Status = "loading" | "signedOut" | "signedIn";

interface AuthState {
  user: User | null;
  status: Status;
  /** Run once at start-up: restores the session if a token is saved. */
  bootstrap: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  status: "loading",

  bootstrap: async () => {
    setOnSessionExpired(() => set({ user: null, status: "signedOut" }));
    try {
      const token = await tokens.getAccess();
      if (!token) {
        set({ status: "signedOut" });
        return;
      }
      const user = await authService.me();
      set({ user, status: "signedIn" });
    } catch {
      await tokens.clear().catch(() => {});
      set({ user: null, status: "signedOut" });
    }
  },

  signIn: async (email, password) => {
    await authService.login(email, password);
    const user = await authService.me();
    set({ user, status: "signedIn" });
  },

  register: async (payload) => {
    await authService.register(payload);
    await authService.login(payload.email, payload.password);
    const user = await authService.me();
    set({ user, status: "signedIn" });
  },

  signOut: async () => {
    try {
      await authService.logout();
    } finally {
      set({ user: null, status: "signedOut" });
    }
  },
}));
