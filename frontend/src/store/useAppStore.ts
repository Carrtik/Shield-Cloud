import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  timestamp: number;
}

interface AppState {
  // Auth
  user: { id: string; email: string; name: string; role: string } | null;
  token: string | null;
  setUser: (user: any, token: string) => void;
  logout: () => void;

  // Risk
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  setRisk: (score: number, level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL') => void;

  // Notifications
  notifications: Notification[];
  addNotification: (message: string, type: Notification['type']) => void;
  removeNotification: (id: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setUser: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),

      riskScore: 0.12,
      riskLevel: 'LOW',
      setRisk: (score, level) => set({ riskScore: score, riskLevel: level }),

      notifications: [],
      addNotification: (message, type) => {
        const id = Math.random().toString(36).slice(2);
        set((state) => ({
          notifications: [...state.notifications, { id, message, type, timestamp: Date.now() }],
        }));
        // Auto-dismiss after 4s
        setTimeout(() => {
          set((state) => ({ notifications: state.notifications.filter((n) => n.id !== id) }));
        }, 4000);
      },
      removeNotification: (id) =>
        set((state) => ({ notifications: state.notifications.filter((n) => n.id !== id) })),
    }),
    {
      name: 'shieldcloud-store',
      version: 1,
      // Only persist auth state, not notifications
      partialize: (state) => ({ user: state.user, token: state.token }),
    }
  )
);
