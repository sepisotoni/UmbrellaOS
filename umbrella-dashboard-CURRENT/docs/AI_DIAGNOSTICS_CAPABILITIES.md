# UmbrellaOS Multi-Provider AI Diagnostics & Intelligence Specification

This document details all AI-powered operations, multi-provider routing architectures, 429 rate-limit fallback mechanisms, and diagnostic pipelines implemented in UmbrellaOS.

---

## 1. Multi-Provider Engine & Auto-Failover Matrix

UmbrellaOS supports unified multi-LLM orchestration across 6 industry-leading AI providers. Each operational task is assigned a **Primary Model** and a **Fallback Model**. If the primary provider returns an HTTP 429 (Rate Limit), an API timeout, or an authentication error, the router automatically falls back to the secondary provider without dropping staff tasks or watchdog checks.

### Supported Providers:
| Provider | Identifier | Default Model | Supported Alternatives | Use Case Strengths |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini** | `gemini` | `gemini-2.5-flash` | `gemini-2.5-pro`, `gemini-1.5-flash` | Fast log tokenization, multimodal chat analysis |
| **Anthropic Claude** | `anthropic` | `claude-3-5-sonnet-20241022` | `claude-3-5-haiku-20241022`, `claude-3-opus` | Complex bytecode decompilation, appeal sincerity reasoning |
| **OpenAI** | `openai` | `gpt-4o` | `gpt-4o-mini`, `o1-preview`, `o3-mini` | General copilot reasoning & JSON structured output |
| **DeepSeek** | `deepseek` | `deepseek-chat` | `deepseek-coder`, `deepseek-r1` | High-speed cost-effective code & stack-trace triage |
| **OpenRouter** | `openrouter` | `anthropic/claude-3.5-sonnet` | `meta-llama/llama-3.3-70b-instruct`, `mistralai/mistral-large` | Redundant gateway routing across 50+ open-source models |
| **Local Ollama Node** | `ollama_local` | `llama3.2:latest` | `qwen2.5-coder:7b`, `mistral:7b` | Air-gapped, zero-cloud private server deployments |

---

## 2. Granular Task Routing & Cascading Table

| Task Identifier | Display Name | Primary Route | Fallback Route | Auto-Failover | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ai_triage` | Crash Log & Post-Mortem Triage | `gemini-2.5-flash` | `claude-3-5-sonnet-20241022` | Enabled | Parses stack dumps and unhandled JVM exceptions |
| `copilot` | UmbrellaOS Copilot Assistant | `claude-3-5-sonnet-20241022` | `gpt-4o` | Enabled | Interactive staff assistant for server administration |
| `appeal_analysis` | Ban Appeal Sincerity & Triage | `gpt-4o` | `gemini-2.5-flash` | Enabled | Evaluates player remorse vs alt evasion indicators |
| `player_profiling` | Player Behavior & Alt Ring Profiling | `deepseek-chat` | `llama3.2:latest` | Enabled | Identifies botting patterns and ban evasion |
| `diagnostics` | Live JVM TPS & Thread Watchdog | `gemini-2.5-flash` | `anthropic/claude-3.5-sonnet` | Enabled | Analyzes MSPT tick deviations and heap leaks |

---

## 3. Rate-Limit (429) & Fault-Tolerant Circuit Breaker

When an AI call is dispatched:
1. **Primary Evaluation**: Check primary provider quota and latency health.
2. **Execution**: Send request with configurable temperature and token bounds.
3. **Exception Interception**:
   - If HTTP `429 Too Many Requests` or network timeout is caught:
   - Mark primary provider as `rate_limited`.
   - Log a failover event in the **Real-Time AI Failover & Cascade Event Stream**.
   - Dispatch payload immediately to the assigned **Fallback Provider & Model**.
   - Return structured response to the dashboard UI seamlessly.

---

## 4. Specific AI Diagnostic Capabilities

### A. Autonomous Crash Post-Mortem & Log Triage (`POST /api/v1/ai/triage`)
- **Root Cause Extraction**: Distinguishes between plugin memory leaks, corrupted chunk coordinates, concurrent modification bugs, and out-of-memory (OOM) heap exhaustion.
- **Impact Radius Assessment**: Determines if the crash threatens player inventory state or world saves.
- **Actionable Resolution Code**: Outputs specific configuration adjustments (e.g. `paper.yml: chunk-system.io-threads: 4`).

### B. GrimAC Anticheat Combat & Movement Vector Analysis (`POST /api/v1/ai/grim-analysis`)
- **Ping/Jitter Compensation Analysis**: Evaluates whether a 3.25m reach check was caused by player ping fluctuation (>150ms variance) or packet spoofing.
- **Pattern Clustering**: Detects closet-cheating software (e.g. 3.05m reach or aim assist rotation smoothing) across 60-second combat telemetry windows.
- **Confidence Scoring**: Returns a confidence rating (0-100%) and recommendation (`AUTO_BAN`, `CONTINUE_MONITORING`, or `DISMISS_FLAG`).

### C. Real-Time Player Chat Translation (`POST /api/v1/ai/translate`)
- **Gaming Slang & Shorthand Preservation**: Accurately interprets Minecraft gaming lingo (`tp to my warp`, `wts maxed sword`, `dia ore`).
- **Toxicity & Slur Screening**: Automatically filters hate speech and obfuscated evasion bypasses across 30+ languages.

### D. Autonomous TPS Forecasting & Self-Healing Watchdogs (`POST /api/v1/ai/tps-forecast`)
- **Preemptive ZGC Garbage Sweep**: Dispatches non-blocking GC invocation when heap fragmentation trend matches imminent freeze patterns.
- **Entity Throttling**: Temporarily throttles passive mob AI tick frequency in heavily loaded chunks.
- **Graceful Instance Failover**: Directs incoming proxy connections to backup nodes if a server's TPS degradation velocity is irrecoverable.

