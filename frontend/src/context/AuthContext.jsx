import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getSession, setSession } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const session = getSession();
    if (!session) {
      setLoading(false);
      return;
    }
    api
      .getProfile()
      .then(setUser)
      .catch(() => setSession(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const session = await api.login({ email, password });
    setSession(session);
    setUser(session.user);
    return session.user;
  }, []);

  const register = useCallback(async (payload) => {
    const session = await api.register(payload);
    setSession(session);
    setUser(session.user);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // best-effort - proceed with local logout regardless
    }
    setSession(null);
    setUser(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    const fresh = await api.getProfile();
    setUser(fresh);
    return fresh;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshProfile, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
