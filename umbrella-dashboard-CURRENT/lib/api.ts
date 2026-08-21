// lib/api.ts — server-only fetch wrapper against umbrella-core.
//
// Every call goes through the generic capability-invoke path
// (POST /api/v1/capabilities/{name}/invoke) except auth, which predates
// the capability registry and keeps its own /api/v1/auth/* router — see
// docs/design/public-rest-api-and-webhooks.md, Decision 4, for why the
// registry-backed domains are capability-invoke-only.
//
// This file has no "use client" / no `fetch` calls made from the browser.
// A bearer token is a bearer token — it never needs to leave the server.

import "server-only";

const BASE_URL = process.env.UMBRELLA_CORE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, headers, ...rest } = init;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const backend = {
  get: <T>(path: string, token?: string) => request<T>(path, { method: "GET", token }),
  post: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), token }),
};

/** Invoke a registry capability by its fully-qualified name. Fully-qualified
 * per step 0's finding — see lib/types.ts DashboardSlot.capability_name. */
export function invokeCapability<T>(name: string, params: unknown, token?: string) {
  return backend.post<T>(`/api/v1/capabilities/${name}/invoke`, params, token);
}
