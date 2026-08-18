'use client';

import {
  createContext,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  getCurrentUser,
  COOKIE_SESSION_TOKEN,
  loginRequest,
  logoutRequest,
  registerRequest,
  stepUpRequest,
  updateCurrentUserProfile,
  type AuthUser,
} from '@/lib/api';

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { id: string; password: string }) => Promise<AuthUser>;
  register: (payload: {
    id: string;
    sid: number;
    name: string;
    phone: string;
    email: string;
    password: string;
  }) => Promise<AuthUser>;
  updateProfile: (payload: {
    name: string;
    phone: string;
    email: string;
  }) => Promise<AuthUser>;
  logout: () => void;
  refreshSession: () => Promise<AuthUser | null>;
  /** 민감한 관리 작업에만 사용할 단기 step-up 토큰을 발급한다. */
  stepUp: (password: string) => Promise<string>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [baseToken, setBaseToken] = useState<string | null>(null);
  const [elevatedToken, setElevatedToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const elevationTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const token = elevatedToken ?? baseToken;

  const clearElevation = useCallback(() => {
    if (elevationTimer.current) {
      clearTimeout(elevationTimer.current);
      elevationTimer.current = null;
    }
    setElevatedToken(null);
  }, []);

  const refreshSession = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser(COOKIE_SESSION_TOKEN);
      setBaseToken(COOKIE_SESSION_TOKEN);
      clearElevation();
      setUser(currentUser);
      return currentUser;
    } catch {
      setBaseToken(null);
      clearElevation();
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [clearElevation]);

  const logout = useCallback(() => {
    void logoutRequest();
    if (elevationTimer.current) clearTimeout(elevationTimer.current);
    startTransition(() => {
      setBaseToken(null);
      setElevatedToken(null);
      setUser(null);
    });
  }, []);

  useEffect(() => {
    void refreshSession();
    const handleUnauthorized = () => logout();
    window.addEventListener('neoespa:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('neoespa:unauthorized', handleUnauthorized);
      if (elevationTimer.current) clearTimeout(elevationTimer.current);
    };
  }, [logout, refreshSession]);

  async function login(credentials: { id: string; password: string }) {
    setIsLoading(true);

    try {
      await loginRequest(credentials.id, credentials.password);
      const currentUser = await getCurrentUser(COOKIE_SESSION_TOKEN);
      startTransition(() => {
        setBaseToken(COOKIE_SESSION_TOKEN);
        setElevatedToken(null);
        setUser(currentUser);
      });
      return currentUser;
    } finally {
      setIsLoading(false);
    }
  }

  async function register(payload: {
    id: string;
    sid: number;
    name: string;
    phone: string;
    email: string;
    password: string;
  }) {
    setIsLoading(true);

    try {
      await registerRequest({
        id: payload.id,
        sid: payload.sid,
        name: payload.name,
        phone: payload.phone,
        email: payload.email,
        ps: payload.password,
      });
      return await login({ id: payload.id, password: payload.password });
    } finally {
      setIsLoading(false);
    }
  }

  async function updateProfile(payload: {
    name: string;
    phone: string;
    email: string;
  }) {
    if (!baseToken || !token) {
      throw new Error('Authentication is required');
    }

    setIsLoading(true);

    try {
      const updatedUser = await updateCurrentUserProfile(payload, token);
      startTransition(() => {
        setUser(updatedUser);
      });
      return updatedUser;
    } finally {
      setIsLoading(false);
    }
  }

  async function stepUp(password: string) {
    if (!baseToken || !user) {
      throw new Error('Authentication is required');
    }

    const elevated = await stepUpRequest(password, baseToken);
    if (elevationTimer.current) clearTimeout(elevationTimer.current);
    startTransition(() => {
      setElevatedToken(elevated.access_token);
    });
    elevationTimer.current = setTimeout(
      () => setElevatedToken(null),
      10 * 60 * 1000,
    );
    return elevated.access_token;
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: Boolean(user && baseToken),
        login,
        register,
        updateProfile,
        logout,
        refreshSession,
        stepUp,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
