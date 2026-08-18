# UmbrellaOS Bug Sweep Report
**Generated:** 2026-08-18  
**Model:** gemini-3.6-flash (explore + verify, parallel)  
**Chunks scanned:** 7 of 7 (⚠️ Chunk 1 — API Routes hit Gemini 503, needs re-scan)  
**Raw findings:** 12 → **Verified:** 11

---

## 🔴 HIGH Severity (4 issues)

### 1. `umbrella-core-CURRENT/services/ai_service.py` — Line 344
| | |
|---|---|
| **Type** | Syntax Error |
| **Confidence** | High |
| **Issue** | File is truncated mid-statement in `review_chat_message`, causing `SyntaxError` on import — this module cannot be loaded at all |
| **Next step** | Complete the truncated statement or restore missing function code |

---

### 2. `umbrella-core-CURRENT/capabilities/hosting.py` — Line 377
| | |
|---|---|
| **Type** | Syntax Error |
| **Confidence** | High |
| **Issue** | Incomplete return statement `return ServerResult.from_model(s` causes `SyntaxError` on import — entire capabilities module fails to load |
| **Next step** | Complete the expression and close the parentheses |

---

### 3. `umbrella-core-CURRENT/models/plugin_command.py` — Line 3
| | |
|---|---|
| **Type** | Crash (ImportError) |
| **Confidence** | High |
| **Issue** | `from database import Base` is an incorrect import path — causes `ImportError`, model is silently omitted from SQLAlchemy metadata |
| **Next step** | Fix import path to the correct `Base` instance and ensure the model is exported in `models/__init__.py` |

---

### 4. `umbrella-core-CURRENT/models/hosting.py` — Line 196
| | |
|---|---|
| **Type** | Data Loss |
| **Confidence** | High |
| **Issue** | Memory and backup byte fields are typed as 32-bit `Integer` — overflows silently on any allocation ≥ 2 GB |
| **Next step** | Change column type from `Integer` to `BigInteger` |

---

### 5. `umbrella-dashboard-CURRENT/app/api/auth/callback/route.ts` — Line 35
| | |
|---|---|
| **Type** | Security — Open Redirect |
| **Confidence** | High |
| **Issue** | Unvalidated OAuth `next` redirect parameter allows attacker to redirect users to untrusted external domains after login |
| **Next step** | Validate `next` against a relative-path-only pattern or an explicit domain whitelist before redirecting |

---

## 🟡 MEDIUM Severity (5 issues)

### 6. `umbrella-core-CURRENT/services/analytics_service.py` — Lines 48–83
| | |
|---|---|
| **Type** | Race Condition |
| **Confidence** | Medium |
| **Issue** | `_increment_stat` uses read-then-write pattern — concurrent events cause `IntegrityError` under load |
| **Next step** | Refactor to atomic DB upsert (`INSERT ... ON CONFLICT DO UPDATE` / `ON DUPLICATE KEY UPDATE`) |

---

### 7. `umbrella-core-CURRENT/models/verification.py` — Line 22
| | |
|---|---|
| **Type** | Wrong Logic (timezone) |
| **Confidence** | Medium |
| **Issue** | `expires_at` default uses naive `datetime.utcnow()` on a `DateTime(timezone=True)` column — produces ambiguous/incorrect comparisons |
| **Next step** | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` |

---

### 8. `umbrella-core-CURRENT/models/user.py` — Line 132
| | |
|---|---|
| **Type** | Wrong Logic (timezone) |
| **Confidence** | Medium |
| **Issue** | `DiscordOAuthPending.expires_at` has the same naive UTC issue as above |
| **Next step** | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` |

---

### 9. `umbrella-dashboard-CURRENT/components/widgets/dashboard-customizer.tsx` — Lines 51–75
| | |
|---|---|
| **Type** | Missing Error Handling |
| **Confidence** | Medium |
| **Issue** | Save and reset handlers mutate UI state without checking `response.ok` — silently succeeds on server errors |
| **Next step** | Check `response.ok` and surface a user-facing error notification on non-2xx status codes |

---

### 10. `umbrella-dashboard-CURRENT/components/widgets/plugin-execution-history.tsx` — Lines 79–91
| | |
|---|---|
| **Type** | Wrong Logic |
| **Confidence** | Medium |
| **Issue** | Pagination links construct URLs using only `offset`, stripping all active query filters — breaks filtered/searched views on page 2+ |
| **Next step** | Clone `URLSearchParams` from current URL before updating `offset` |

---

### 11. `umbrella-sdk-ts/src/client.ts` — Line 127
| | |
|---|---|
| **Type** | Missing Error Handling |
| **Confidence** | Medium |
| **Issue** | `unwrap()` calls `res.json()` unconditionally — crashes on `204 No Content` or non-JSON `2xx` responses |
| **Next step** | Check `response.status !== 204` and `Content-Type: application/json` header before calling `res.json()` |

---

## 🔵 LOW Severity (1 issue)

### 12. `umbrella-core-CURRENT/services/anticheat_service.py` — Lines 28–63
| | |
|---|---|
| **Type** | Dead Code |
| **Confidence** | Low |
| **Issue** | `_ai_confidence_review` helper is defined but never called |
| **Next step** | Wire into the relevant workflow or remove if obsolete |

---

## ⚠️ Coverage Gap

**Chunk 1 — `umbrella-core-CURRENT/api/`** (43 files) hit a Gemini 503 during the sweep and was **not scanned**. This is the API routes layer — potentially the highest-risk surface for auth/input-validation bugs.

**Recommended:** Re-run the sweep on this chunk alone when Gemini demand normalizes, or ask me to run it now.

---

## Usage Summary
| Provider | Role | Status |
|---|---|---|
| Gemini 3.6 Flash | Explore (6/7 chunks) | ✅ Done |
| Gemini 3.6 Flash | Verification pass | ✅ Done |
| Gemini 3.6 Flash | API Routes chunk | ❌ 503 — needs re-scan |
| Groq qwen3.6-27b | (skipped — 8k TPM too low) | — |
