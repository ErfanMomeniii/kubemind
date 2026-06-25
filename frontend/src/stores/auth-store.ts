import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: { id: string; email: string; name: string; orgId: string | null } | null;
  selectedClusterId: string | null;
  setAuth: (tokens: { accessToken: string; refreshToken: string }, user: AuthState["user"]) => void;
  setSelectedClusterId: (id: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      selectedClusterId: null,
      setAuth: (tokens, user) =>
        set({
          accessToken: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          user,
        }),
      setSelectedClusterId: (id) => set({ selectedClusterId: id }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, user: null, selectedClusterId: null }),
    }),
    { name: "kubemind-auth" },
  ),
);
