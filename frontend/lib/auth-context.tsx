"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { User } from "@/types";
import { api, getApiAuthToken, setApiAuthToken } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthModalOpen: boolean;
  authModalTab: "login" | "register";
  openAuthModal: (tab?: "login" | "register") => void;
  closeAuthModal: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalTab, setAuthModalTab] = useState<"login" | "register">("login");

  // Initialize session from localStorage and fetch current user
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = getApiAuthToken();
      if (storedToken) {
        setToken(storedToken);
        try {
          const currentUser = await api.getCurrentUser();
          setUser(currentUser);
        } catch {
          // Token expired or invalid
          setApiAuthToken(null);
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.login(email, password);
    setToken(response.accessToken);
    setUser(response.user);
    setIsAuthModalOpen(false);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const response = await api.register(email, password, fullName);
    setToken(response.accessToken);
    setUser(response.user);
    setIsAuthModalOpen(false);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setToken(null);
      setUser(null);
      setApiAuthToken(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
    } catch {
      setUser(null);
      setToken(null);
      setApiAuthToken(null);
    }
  }, []);

  const openAuthModal = useCallback((tab: "login" | "register" = "login") => {
    setAuthModalTab(tab);
    setIsAuthModalOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => {
    setIsAuthModalOpen(false);
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading,
      isAuthenticated: Boolean(user && token),
      login,
      register,
      logout,
      isAuthModalOpen,
      authModalTab,
      openAuthModal,
      closeAuthModal,
      refreshUser,
    }),
    [
      user,
      token,
      isLoading,
      isAuthModalOpen,
      authModalTab,
      login,
      register,
      logout,
      openAuthModal,
      closeAuthModal,
      refreshUser,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
