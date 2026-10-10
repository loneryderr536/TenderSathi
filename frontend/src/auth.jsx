import { createContext, useContext, useEffect, useState } from "react";
import { LOGGED_OUT_EVENT, clearCompanyId, clearSession, getUser, request, setCompanyId, setSession } from "./api";

const AuthContext = createContext(null);

/** Where each role lands after logging in, and which views it may open. */
export const HOME = { business: "/", government: "/gov", platform: "/admin" };
export const VIEWS = { business: ["business"], government: ["gov"], platform: ["business", "gov", "admin"] };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getUser);

  useEffect(() => {
    const onLoggedOut = () => setUser(null);
    window.addEventListener(LOGGED_OUT_EVENT, onLoggedOut);
    return () => window.removeEventListener(LOGGED_OUT_EVENT, onLoggedOut);
  }, []);

  function logIn({ token, user: next }) {
    setSession(token, next);
    // A business owner's pages work on their own profile; a new owner fills one in first.
    if (next.role === "business") {
      if (next.company_id) setCompanyId(next.company_id);
      else clearCompanyId();
    }
    setUser(next);
  }

  async function logOut() {
    await request("/auth/logout", { method: "POST" }).catch(() => {});
    clearSession();
    clearCompanyId();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, logIn, logOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
