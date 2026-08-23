import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, UserSchema } from '../lib/api';

export type NavigationTab = 
  | 'overview'
  | 'players'
  | 'moderation'
  | 'appeals'
  | 'staff'
  | 'verification'
  | 'alts'
  | 'servers'
  | 'console'
  | 'plugins'
  | 'ai-tasks'
  | 'audit'
  | 'feature-flags'
  | 'settings'
  | 'login';

export interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
}

interface DashboardContextType {
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  currentUser: UserSchema | null;
  setCurrentUser: (user: UserSchema | null) => void;
  sessionToken: string | null;
  setSessionToken: (token: string | null) => void;
  adminKey: string | null;
  setAdminKey: (key: string | null) => void;
  isDisconnected: boolean;
  healthInfo: { status: string; version: string; database: string; redis?: string } | null;
  checkHealth: () => Promise<boolean>;
  selectedPlayerUuid: string | null;
  setSelectedPlayerUuid: (uuid: string | null) => void;
  selectedAppealId: string | null;
  setSelectedAppealId: (id: string | null) => void;
  selectedServerId: string | null;
  setSelectedServerId: (id: string | null) => void;
  toasts: ToastNotification[];
  addToast: (toast: Omit<ToastNotification, 'id' | 'timestamp'>) => void;
  removeToast: (id: string) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  logout: () => Promise<void>;
  navigateToPlayer: (uuid: string) => void;
  navigateToAppeal: (appealId: string) => void;
  navigateToServerConsole: (serverId: string) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Navigation State
  const [activeTab, setActiveTab] = useState<NavigationTab>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  // Auth State (Tokens stored ONLY in memory, never in localStorage!)
  const [sessionToken, setSessionTokenState] = useState<string | null>(null);
  const [adminKey, setAdminKeyState] = useState<string | null>(() => api.getAdminKey());
  const [currentUser, setCurrentUser] = useState<UserSchema | null>(null);

  // Health / Connection State
  const [isDisconnected, setIsDisconnected] = useState<boolean>(false);
  const [healthInfo, setHealthInfo] = useState<{ status: string; version: string; database: string; redis?: string } | null>(null);

  // Deep Link Selection State
  const [selectedPlayerUuid, setSelectedPlayerUuid] = useState<string | null>(null);
  const [selectedAppealId, setSelectedAppealId] = useState<string | null>(null);
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null);

  // Toast Notifications
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const addToast = useCallback((toast: Omit<ToastNotification, 'id' | 'timestamp'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const newToast: ToastNotification = {
      ...toast,
      id,
      timestamp: new Date().toISOString(),
    };
    setToasts((prev) => [...prev, newToast]);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const setSessionToken = useCallback((token: string | null) => {
    setSessionTokenState(token);
    api.setSessionToken(token);
  }, []);

  const setAdminKey = useCallback((key: string | null) => {
    setAdminKeyState(key);
    api.setAdminKey(key);
  }, []);

  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      const data = await api.getHealth();
      setHealthInfo(data);
      setIsDisconnected(false);
      return true;
    } catch {
      setIsDisconnected(true);
      return false;
    }
  }, []);

  // Health check on initial mount & periodic 30s poll
  useEffect(() => {
    checkHealth();
    const interval = setInterval(() => {
      checkHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Check URL query parameters for Discord OAuth callback on startup
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');

    if (code && state) {
      // Clear URL params cleanly without reloading
      window.history.replaceState({}, document.title, window.location.pathname);
      const redirectUri = `${window.location.origin}/`;
      api.discordCallback(code, state, redirectUri)
        .then((res) => {
          setSessionToken(res.token);
          setCurrentUser(res.user);
          addToast({
            type: 'success',
            title: 'Authentication Successful',
            message: `Welcome back, ${res.user.username}!`,
          });
          setActiveTab('overview');
        })
        .catch((err) => {
          addToast({
            type: 'error',
            title: 'Discord Login Failed',
            message: err.message || 'Unable to authenticate with Discord.',
          });
          setActiveTab('login');
        });
    }
  }, [setSessionToken, addToast]);

  // Load current user profile if session token exists
  useEffect(() => {
    if (sessionToken) {
      api.getMe()
        .then((user) => setCurrentUser(user))
        .catch(() => {
          // Token invalid or expired
          setSessionToken(null);
          setCurrentUser(null);
        });
    }
  }, [sessionToken, setSessionToken]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Ignore network errors on logout
    }
    setSessionToken(null);
    setCurrentUser(null);
    setActiveTab('login');
    addToast({
      type: 'info',
      title: 'Logged Out',
      message: 'You have been securely signed out.',
    });
  }, [setSessionToken, addToast]);

  const navigateToPlayer = useCallback((uuid: string) => {
    setSelectedPlayerUuid(uuid);
    setActiveTab('players');
  }, []);

  const navigateToAppeal = useCallback((appealId: string) => {
    setSelectedAppealId(appealId);
    setActiveTab('appeals');
  }, []);

  const navigateToServerConsole = useCallback((serverId: string) => {
    setSelectedServerId(serverId);
    setActiveTab('console');
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  return (
    <DashboardContext.Provider
      value={{
        activeTab,
        setActiveTab,
        currentUser,
        setCurrentUser,
        sessionToken,
        setSessionToken,
        adminKey,
        setAdminKey,
        isDisconnected,
        healthInfo,
        checkHealth,
        selectedPlayerUuid,
        setSelectedPlayerUuid,
        selectedAppealId,
        setSelectedAppealId,
        selectedServerId,
        setSelectedServerId,
        toasts,
        addToast,
        removeToast,
        sidebarCollapsed,
        setSidebarCollapsed,
        toggleSidebar,
        logout,
        navigateToPlayer,
        navigateToAppeal,
        navigateToServerConsole,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = (): DashboardContextType => {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
};
