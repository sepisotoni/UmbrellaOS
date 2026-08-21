// lib/session.ts — server-only session helpers.
//
// The dashboard holds no auth state of its own: the cookie's value is the
// literal opaque session token umbrella-core issues from
// POST /api/v1/auth/discord/callback (services/roles_service.py's
// DEFAULT_ROLES / DEFAULT_PERMISSIONS is the actual source of truth for
// what a role can do — this file never hardcodes a role name to a
// permission set, it always asks the backend via /auth/me).

import "server-only";
import { cookies } from "next/headers";
import { backend, ApiError } from "./api";
import type { User } from "./types";

export const SESSION_COOKIE = "umbrella_session";

export async function getSessionToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? null;
}

/** Resolves the current user (with role + full permission list) from the
 * real backend, or null if there's no session / it's expired or revoked.
 * Never caches across requests — permission changes (a role edit) must be
 * reflected on next navigation, not stale until re-login. */
export async function getSession(): Promise<{ token: string; user: User } | null> {
  const token = await getSessionToken();
  if (!token) return null;
  try {
    const user = await backend.get<User>("/api/v1/auth/me", token);
    return { token, user };
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      return null;
    }
    throw err;
  }
}

export function hasPermission(user: User, permission: string): boolean {
  // owner/admin roles are granted every permission key server-side
  // (services/roles_service.py DEFAULT_ROLES) — no client-side "is owner"
  // special-casing needed, the permissions array already reflects it.
  return user.permissions.includes(permission);
}

export function hasAnyPermission(user: User, permissions: string[]): boolean {
  return permissions.some((p) => hasPermission(user, p));
}
