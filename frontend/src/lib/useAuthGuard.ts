"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { me } from "@/lib/api";
import { clearSession, getStoredUser, getToken, type AuthUser, type Role } from "@/lib/auth";

type UseAuthGuardOptions = {
  allowedRoles: Role[];
  redirectPath?: string;
};

export function useAuthGuard({ allowedRoles, redirectPath = "/" }: UseAuthGuardOptions) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getToken();
    const stored = getStoredUser();
    if (!token || !stored) {
      return null;
    }
    return allowedRoles.includes(stored.role) ? stored : null;
  });
  const [loading, setLoading] = useState(() => {
    const token = getToken();
    const stored = getStoredUser();
    return !(token && stored && allowedRoles.includes(stored.role));
  });
  const allowedRolesKey = allowedRoles.join("|");

  useEffect(() => {
    let active = true;
    const allowed = new Set(allowedRolesKey.split("|") as Role[]);

    async function verifyRole() {
      const token = getToken();
      const storedUser = getStoredUser();

      if (!token) {
        clearSession();
        router.replace(redirectPath);
        if (active) setLoading(false);
        return;
      }

      if (storedUser && allowed.has(storedUser.role)) {
        if (active) {
          setUser(storedUser);
          setLoading(false);
        }
      } else if (active) {
        setLoading(true);
      }

      try {
        const currentUser = await me();
        if (!allowed.has(currentUser.role)) {
          clearSession();
          router.replace(redirectPath);
          return;
        }
        if (active) {
          setUser(currentUser);
        }
      } catch {
        clearSession();
        router.replace(redirectPath);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void verifyRole();

    return () => {
      active = false;
    };
  }, [allowedRolesKey, redirectPath, router]);

  const logout = useCallback(() => {
    clearSession();
    router.replace(redirectPath);
  }, [redirectPath, router]);

  return { loading, user, logout };
}
