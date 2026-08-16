/**
 * src/client.ts — thin typed-fetch wrapper over UmbrellaOS's generic
 * capability-invoke REST surface.
 *
 * Deliberately NOT a per-capability generated method (`client.marketplace
 * .install.install(...)`, etc.) — see this package's README, "Why a thin
 * wrapper instead of a full generated client," for the reasoning. The
 * short version: the entire public REST surface is exactly two routes
 * (`GET /api/v1/capabilities`, `POST /api/v1/capabilities/{name}/invoke`
 * — see `registry/adapters/rest.py`'s own module docstring in
 * umbrella-core), so a heavier generator (openapi-generator-cli's
 * typescript-fetch target) would produce one generated method per
 * capability that all do the same thing with a different string literal
 * baked in — more generated surface to keep in sync, not less risk.
 * `openapi-typescript`'s output (`generated-types.ts`) already gives real
 * compile-time types for `CapabilitySummary` and the invoke request/
 * response shape; this file is the part a generator can't produce on its
 * own — knowing which header carries auth, and that a 401 vs. a 422
 * vs. the capability's own error shape need different handling.
 */
import type { components } from "./generated-types.js";

export type CapabilitySummary = components["schemas"]["CapabilitySummary"];

export interface UmbrellaClientOptions {
  /** Base URL of the umbrella-core instance, e.g. "https://umbrella.example.com". No trailing slash. */
  baseUrl: string;
  /**
   * Scoped API key (`X-Api-Key` header) — the only auth mode this SDK
   * supports. Session-cookie and admin-key auth exist server-side (see
   * `api/middleware/api_key_auth.py::require_capability_auth`) but are
   * for the dashboard and bootstrap/CLI use, not external consumers —
   * an external consumer of this SDK should always be using a scoped
   * key from `identity.apikey.create`.
   */
  apiKey: string;
  /**
   * Optional Discord snowflake to act on behalf of, via the
   * `X-Discord-User-Id` header — only takes effect server-side if this
   * key carries the `identity.discord_delegate` permission (see
   * `registry/adapters/rest.py`'s `invoke_capability` docstring); silently
   * ignored by the server otherwise, so it's safe to always pass this for
   * a delegate-capable key without checking permissions client-side first.
   */
  discordUserId?: string;
  /** Override fetch (e.g. for testing, or a non-global fetch runtime). Defaults to global fetch. */
  fetchFn?: typeof fetch;
}

export class UmbrellaApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "UmbrellaApiError";
  }
}

export class UmbrellaClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly discordUserId?: string;
  private readonly fetchFn: typeof fetch;

  constructor(options: UmbrellaClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.apiKey = options.apiKey;
    this.discordUserId = options.discordUserId;
    this.fetchFn = options.fetchFn ?? fetch;
  }

  private headers(): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Api-Key": this.apiKey,
    };
    if (this.discordUserId) {
      headers["X-Discord-User-Id"] = this.discordUserId;
    }
    return headers;
  }

  /** GET /api/v1/capabilities — every registered capability and its param schema. */
  async listCapabilities(): Promise<CapabilitySummary[]> {
    const res = await this.fetchFn(`${this.baseUrl}/api/v1/capabilities`, {
      headers: this.headers(),
    });
    return this.unwrap<CapabilitySummary[]>(res);
  }

  /**
   * POST /api/v1/capabilities/{name}/invoke — call any registered
   * capability by name. `TResult` is left to the caller to specify
   * (e.g. `client.invoke<MyResult>("marketplace.install.list", {})`) —
   * the server response shape genuinely varies per capability, and this
   * generic surface has no per-capability result type to check against
   * without a second, per-capability code-generation pass this package
   * deliberately doesn't do (see the module docstring above).
   */
  async invoke<TResult = unknown>(name: string, params: Record<string, unknown> = {}): Promise<TResult> {
    const res = await this.fetchFn(`${this.baseUrl}/api/v1/capabilities/${encodeURIComponent(name)}/invoke`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(params),
    });
    return this.unwrap<TResult>(res);
  }

  private async unwrap<T>(res: Response): Promise<T> {
    if (!res.ok) {
      let body: unknown;
      try {
        body = await res.json();
      } catch {
        body = await res.text();
      }
      throw new UmbrellaApiError(`UmbrellaOS API request failed: ${res.status} ${res.statusText}`, res.status, body);
    }
    return (await res.json()) as T;
  }
}
