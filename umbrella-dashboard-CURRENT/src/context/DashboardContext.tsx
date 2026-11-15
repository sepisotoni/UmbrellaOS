import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, UserSchema } from '../lib/api';
import { initializeSupabase, supabase } from '../lib/supabase';

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
  | 'knowledge'
  | 'settings'
  | 'discord'
  | 'access-denied'
  | '404'
  | 'login';

export function canUserAccessTab(tab: NavigationTab, user: UserSchema | null): boolean {
  if (tab === 'login' || tab === 'access-denied' || tab === '404') return true;
  if (!user) return false;

  const requiredPermissions: Partial<Record<NavigationTab, string[]>> = {
    overview: ['players.view'],
    discord: ['discord.view', 'discord.manage', 'settings.view'],
    players: ['players.view'],
    moderation: ['moderation.kick', 'moderation.warn', 'moderation.ban', 'punishments.view'],
    appeals: ['appeals.view'],
    staff: ['roles.manage'],
    verification: ['verification.link.view', 'verification.link.manage'],
    alts: ['players.view'],
    servers: ['hosting.server.view', 'server.control'],
    console: ['hosting.server.control', 'server.control'],
    plugins: ['marketplace.install.view', 'plugin.sandbox.view'],
    'ai-tasks': ['operational_intelligence.view', 'investigation.run'],
    audit: ['audit.view'],
    'feature-flags': ['feature_flags.view'],
    knowledge: ['knowledge.entry.search'],
    settings: ['settings.view', 'settings.manage'],
  };
  const permissions = new Set(user.permissions || []);
  return (requiredPermissions[tab] || []).some((permission) => permissions.has(permission));
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
  authConfigLoaded: boolean;
  authConfigError: string | null;
  sessionToken: string | null;
  setSessionToken: (token: string | null) => void;
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
  // Supabase MFA challenge and re-enrollment state.
  mfaPending: { factorId: string; challengeId: string } | null;
  mfaEnrollmentRequired: boolean;
  completeMfa: (totpCode: string) => Promise<void>;
  dismissMfa: () => void;
  setMfaEnrollmentRequired: (required: boolean) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Navigation State
  const [activeTab, setActiveTab] = useState<NavigationTab>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(
    // Default to collapsed on mobile (< 768px) so the sidebar doesn't eat the viewport
    typeof window !== 'undefined' && window.innerWidth < 768
  );

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

  // Supabase Auth owns browser sessions and refreshes access tokens.
  const [sessionToken, setSessionTokenState] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserSchema | null>(null);
  const [authConfigLoaded, setAuthConfigLoaded] = useState(false);
  const [authConfigError, setAuthConfigError] = useState<string | null>(null);
  const [mfaPending, setMfaPending] = useState<{ factorId: string; challengeId: string } | null>(null);
  const [mfaEnrollmentRequired, setMfaEnrollmentRequired] = useState(false);

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

  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      const data = await api.getHealth();
      setHealthInfo(data);
      setIsDisconnected((prev) => (prev ? false : prev));
      return true;
    } catch {
      setIsDisconnected((prev) => (prev ? prev : true));
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

  // Supabase Auth handles OAuth callbacks and owns the refreshable browser session.
  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | null = null;
    const loadUser = async (
      authClient: NonNullable<typeof supabase>,
      accessToken: string,
    ) => {
      api.setSessionToken(accessToken);
      try {
        const user = await api.getMe();
        if (!active) return;
        setCurrentUser(user);
        const { data: assurance, error: assuranceError } =
          await authClient.auth.mfa.getAuthenticatorAssuranceLevel();
        if (assuranceError) throw assuranceError;
        const { data: factors, error: factorsError } = await authClient.auth.mfa.listFactors();
        if (factorsError) throw factorsError;
        const factor = factors.totp.find((candidate) => candidate.status === 'verified');
        if (user.mfa_enabled && !factor && active) {
          setMfaEnrollmentRequired(true);
        } else if (
          factor &&
          assurance.nextLevel === 'aal2' &&
          assurance.currentLevel !== 'aal2'
        ) {
          const { data: challenge, error: challengeError } =
            await authClient.auth.mfa.challenge({ factorId: factor.id });
          if (challengeError) throw challengeError;
          if (active) setMfaPending({ factorId: factor.id, challengeId: challenge.id });
        }
      } catch (error: any) {
        if (!active) return;
        setCurrentUser(null);
        setSessionToken(null);
        addToast({
          type: 'error',
          title: 'Sign-in failed',
          message: error?.message || 'Supabase Auth could not verify this staff account.',
        });
        await authClient.auth.signOut({ scope: 'local' });
      }
    };

    const initializeAuth = async () => {
      try {
        const config = await api.getPublicAuthConfig();
        if (!active) return;

        const authClient = initializeSupabase(
          config.supabase_url,
          config.supabase_publishable_key,
        );
        const { data: listener } = authClient.auth.onAuthStateChange((_event, session) => {
          const token = session?.access_token ?? null;
          setSessionToken(token);
          setMfaPending(null);
          if (token) {
            window.setTimeout(() => void loadUser(authClient, token), 0);
          } else {
            setCurrentUser(null);
            setMfaEnrollmentRequired(false);
          }
        });
        unsubscribe = () => listener.subscription.unsubscribe();

        const { data, error } = await authClient.auth.getSession();
        if (!active) return;
        if (error) throw error;

        setAuthConfigError(null);
        setAuthConfigLoaded(true);
        const token = data.session?.access_token ?? null;
        setSessionToken(token);
        if (token) void loadUser(authClient, token);
      } catch (error: any) {
        if (!active) return;
        setAuthConfigError(error?.message || 'Core could not provide Supabase Auth settings.');
        setAuthConfigLoaded(true);
      }
    };

    void initializeAuth();
    return () => {
      active = false;
      unsubscribe?.();
    };
  }, [addToast, setSessionToken]);

  const completeMfa = useCallback(async (totpCode: string) => {
    if (!supabase || !mfaPending) return;
    const { error } = await supabase.auth.mfa.verify({
      factorId: mfaPending.factorId,
      challengeId: mfaPending.challengeId,
      code: totpCode,
    });
    if (error) throw error;
    setMfaPending(null);
    await supabase.auth.refreshSession();
    addToast({
      type: 'success',
      title: 'Authentication Successful',
      message: 'Supabase Auth MFA verified.',
    });
    setActiveTab('overview');
  }, [mfaPending, addToast]);

  const dismissMfa = useCallback(() => {
    setMfaPending(null);
    if (supabase) void supabase.auth.signOut({ scope: 'local' });
  }, []);

  const logout = useCallback(async () => {
    try {
      await supabase?.auth.signOut({ scope: 'global' });
    } finally {
      setSessionToken(null);
      setCurrentUser(null);
      setMfaPending(null);
      setMfaEnrollmentRequired(false);
      setActiveTab('login');
    }
    addToast({
      type: 'info',
      title: 'Signed out',
      message: 'Your Supabase Auth session has been cleared.',
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
    return canUserAccessTab(tab, currentUser);
  }, [currentUser]);

  return (
    <DashboardContext.Provider
      value={{
        activeTab,
        setActiveTab,
        currentUser,
        setCurrentUser,
        authConfigLoaded,
        authConfigError,
        sessionToken,
        setSessionToken,
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
        mfaPending,
        mfaEnrollmentRequired,
        completeMfa,
        dismissMfa,
        setMfaEnrollmentRequired,
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
