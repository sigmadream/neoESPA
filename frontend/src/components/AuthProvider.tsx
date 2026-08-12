'use client';

import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useState,
} from 'react';

import {
  getCurrentUser,
  loginRequest,
  registerRequest,
  stepUpRequest,
  updateCurrentUserProfile,
  type AuthUser,
} from '@/lib/api';

const STORAGE_KEY = 'neoespa.auth.session';

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
  /** 민감한 관리 작업 전 재인증. 성공하면 step-up 토큰으로 세션을 교체한다. */
  stepUp: (password: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type StoredSession = {
  token: string;
  user: AuthUser;
};

function readStoredSession(): StoredSession | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function writeStoredSession(session: StoredSession | null) {
  if (typeof window === 'undefined') {
    return;
  }

  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function refreshSession() {
    const storedSession = readStoredSession();
    if (!storedSession?.token) {
      setToken(null);
      setUser(null);
      setIsLoading(false);
      return null;
    }

    try {
      const currentUser = await getCurrentUser(storedSession.token);
      setToken(storedSession.token);
      setUser(currentUser);
      writeStoredSession({ token: storedSession.token, user: currentUser });
      return currentUser;
    } catch {
      writeStoredSession(null);
      setToken(null);
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refreshSession();
  }, []);

  async function login(credentials: { id: string; password: string }) {
    setIsLoading(true);

    try {
      const authToken = await loginRequest(credentials.id, credentials.password);
      const currentUser = await getCurrentUser(authToken.access_token);
      writeStoredSession({ token: authToken.access_token, user: currentUser });
      startTransition(() => {
        setToken(authToken.access_token);
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
    if (!token) {
      throw new Error('Authentication is required');
    }

    setIsLoading(true);

    try {
      const updatedUser = await updateCurrentUserProfile(payload, token);
      writeStoredSession({ token, user: updatedUser });
      startTransition(() => {
        setUser(updatedUser);
      });
      return updatedUser;
    } finally {
      setIsLoading(false);
    }
  }

  async function stepUp(password: string) {
    if (!token || !user) {
      throw new Error('Authentication is required');
    }

    const elevated = await stepUpRequest(password, token);
    writeStoredSession({ token: elevated.access_token, user });
    startTransition(() => {
      setToken(elevated.access_token);
    });
  }

  function logout() {
    writeStoredSession(null);
    startTransition(() => {
      setToken(null);
      setUser(null);
    });
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: Boolean(user && token),
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
