export type Role = "admin" | "lawyer";

export type AuthUser = {
  user_id: string;
  email: string;
  role: Role;
};

export type LoginResult = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

const TOKEN_KEY = "atticus_token";
const USER_KEY = "atticus_user";
const EXPIRES_KEY = "atticus_expires_at";
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;

export function saveSession(result: LoginResult): void {
  if (typeof window === "undefined") return;
  const expiresAt = Date.now() + SESSION_TTL_MS;
  sessionStorage.setItem(TOKEN_KEY, result.access_token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(result.user));
  sessionStorage.setItem(EXPIRES_KEY, String(expiresAt));
  document.cookie = `atticus_role=${result.user.role}; Path=/; SameSite=Strict`;
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  sessionStorage.removeItem(EXPIRES_KEY);
  document.cookie = "atticus_role=; Max-Age=0; Path=/; SameSite=Strict";
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const expiresAtRaw = sessionStorage.getItem(EXPIRES_KEY);
  if (!expiresAtRaw || Number(expiresAtRaw) < Date.now()) {
    clearSession();
    return null;
  }
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}
