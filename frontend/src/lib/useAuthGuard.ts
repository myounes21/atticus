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
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser());
  const [loading, setLoading] = useState(true);
  const allowedRolesKey = allowedRoles.join("|");

  useEffect(() => {
    let active = true;
    const allowed = new Set(allowedRolesKey.split("|") as Role[]);

    async function verifyRole() {
      if (!getToken()) {
        clearSession();
        router.replace(redirectPath);
        if (active) setLoading(false);
        return;
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
