import { create } from "zustand";
import { User, authService } from "../services/auth";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isAuthenticated: false,

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const user = await authService.me();
      set({ user, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      await authService.login(email, password);
      const user = await authService.me();
      set({ user, isAuthenticated: true });
    } finally {
      set({ isLoading: false });
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      const { SecureStore } = await import("expo-secure-store");
      const refresh = await SecureStore.getItemAsync("refresh_token");
      if (refresh) await authService.logout(refresh);
    } finally {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));