// Lightweight client-side auth state. The token is a server-signed JWT; the
// backend is the authority on permissions — role stored here is only used to
// tailor the UI (it never grants access on its own).
export type AuthUser = {
  id: string;
  email: string;
  name: string;
  role: "admin" | "recruiter" | string;
  is_active: boolean;
};

const TOKEN_KEY = "sis_token";
const USER_KEY = "sis_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setStoredUser(user: AuthUser) {
  if (typeof window !== "undefined") localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// Routes that must remain reachable without a staff login (candidate flows + login).
export const PUBLIC_PATH_PREFIXES = ["/login", "/availability/", "/confirm/"];

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATH_PREFIXES.some((p) =>
    p.endsWith("/") ? pathname.startsWith(p) : pathname === p
  );
}
