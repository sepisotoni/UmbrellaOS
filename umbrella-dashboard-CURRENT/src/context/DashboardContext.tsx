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
  | 'discord'
  | 'access-denied'
  | '404'
  | 'login';

export const TAB_ROLE_CLEARANCE: Record<NavigationTab, string[]> = {
  overview: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff', 'viewer'],
  discord: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff'],
  players: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff'],
  moderation: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'staff'],
  appeals: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff'],
  staff: ['superadmin', 'owner', 'admin'],
  verification: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff'],
  alts: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'staff'],
  servers: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff'],
  console: ['superadmin', 'owner', 'admin', 'developer'],
  plugins: ['superadmin', 'owner', 'admin', 'developer'],
  'ai-tasks': ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'staff'],
  audit: ['superadmin', 'owner', 'admin', 'developer'],
  'feature-flags': ['superadmin', 'owner', 'admin', 'developer'],
  settings: ['superadmin', 'owner', 'admin'],
  'access-denied': ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff', 'viewer'],
  '404': ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff', 'viewer'],
  login: ['superadmin', 'owner', 'admin', 'developer', 'moderator', 'support', 'helper', 'staff', 'viewer'],
};

export function canUserAccessTab(tab: NavigationTab, user: UserSchema | null, adminKey?: string | null): boolean {
  if (tab === 'login' || tab === 'access-denied' || tab === '404') return true;
  if (adminKey && adminKey.trim().length > 0) return true;
  if (!user) return false;
  
  const userRole = (user.role || 'viewer').toLowerCase();
  if (userRole === 'superadmin' || userRole === 'owner') return true;

  const allowedRoles = TAB_ROLE_CLEARANCE[tab] || [];
  return allowedRoles.includes(userRole);
}

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
  canAccessTab: (tab: NavigationTab) => boolean;
  // Wallpaper and Brand visual settings
  showDoodles: boolean;
  setShowDoodles: (show: boolean) => void;
  doodleOpacity: number;
  setDoodleOpacity: (opacity: number) => void;
  selectedBrand: 'os' | 'core' | 'bot' | 'dashboard';
  setSelectedBrand: (brand: 'os' | 'core' | 'bot' | 'dashboard') => void;
  discordInvite: string;
  setDiscordInvite: (url: string) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Navigation State
  const [activeTab, setActiveTab] = useState<NavigationTab>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  // Discord Invite URL
  const [discordInvite, setDiscordInviteState] = useState<string>(() => {
    const saved = localStorage.getItem('umbrella_discord_invite');
    return saved || (import.meta as any).env?.VITE_DISCORD_INVITE || 'https://discord.gg/umbrella';
  });

  const setDiscordInvite = useCallback((url: string) => {
    setDiscordInviteState(url);
    localStorage.setItem('umbrella_discord_invite', url);
  }, []);

  // Wallpaper & Theme state
  const [showDoodles, setShowDoodles] = useState<boolean>(() => {
    const saved = localStorage.getItem('umbrella_show_doodles');
    return saved !== null ? saved === 'true' : true;
  });
  const [doodleOpacity, setDoodleOpacityState] = useState<number>(() => {
    const saved = localStorage.getItem('umbrella_doodle_opacity');
    return saved !== null ? parseFloat(saved) : 0.08;
  });
  const [selectedBrand, setSelectedBrandState] = useState<'os' | 'core' | 'bot' | 'dashboard'>(() => {
    const saved = localStorage.getItem('umbrella_selected_brand');
    return (saved as any) || 'os';
  });

  const setDoodleOpacity = useCallback((op: number) => {
    setDoodleOpacityState(op);
    localStorage.setItem('umbrella_doodle_opacity', op.toString());
  }, []);

  const handleToggleDoodles = useCallback((show: boolean) => {
    setShowDoodles(show);
    localStorage.setItem('umbrella_show_doodles', show ? 'true' : 'false');
  }, []);

  const setSelectedBrand = useCallback((brand: 'os' | 'core' | 'bot' | 'dashboard') => {
    setSelectedBrandState(brand);
    localStorage.setItem('umbrella_selected_brand', brand);
  }, []);

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

  const canAccessTab = useCallback((tab: NavigationTab) => {
    return canUserAccessTab(tab, currentUser, adminKey);
  }, [currentUser, adminKey]);

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
        canAccessTab,
        showDoodles,
        setShowDoodles: handleToggleDoodles,
        doodleOpacity,
        setDoodleOpacity,
        selectedBrand,
        setSelectedBrand,
        discordInvite,
        setDiscordInvite,
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
