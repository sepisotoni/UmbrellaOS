/**
 * Default empty state templates for dashboard startup before backend sync.
 * All collections start empty (no mock/fabricated data).
 */

import {
  MinecraftServer,
  NodeInfrastructure,
  PlayerRecord,
  PunishmentRecord,
  GrimACViolation,
  AltAccountCluster,
  AppealTicket,
  ConsoleLogMessage,
  CrashReport,
  PluginMeta,
  SnapshotCheckpoint,
  AutomationCronTask,
  WebhookSubscription,
  ApiKeyRecord,
  FeatureFlagRecord,
  AICopilotMessage,
  AIEngineConfiguration
} from '../types/dashboard';

export const EMPTY_SERVERS: MinecraftServer[] = [];
export const EMPTY_NODES: NodeInfrastructure[] = [];
export const EMPTY_PLAYERS: PlayerRecord[] = [];
export const EMPTY_PUNISHMENTS: PunishmentRecord[] = [];
export const EMPTY_GRIM_VIOLATIONS: GrimACViolation[] = [];
export const EMPTY_ALT_CLUSTERS: AltAccountCluster[] = [];
export const EMPTY_APPEALS: AppealTicket[] = [];
export const EMPTY_LOGS: ConsoleLogMessage[] = [];
export const EMPTY_COPILOT_MESSAGES: AICopilotMessage[] = [];
export const EMPTY_CRASH_REPORTS: CrashReport[] = [];
export const EMPTY_PLUGINS: PluginMeta[] = [];
export const EMPTY_SNAPSHOTS: SnapshotCheckpoint[] = [];
export const EMPTY_CRONS: AutomationCronTask[] = [];
export const EMPTY_WEBHOOKS: WebhookSubscription[] = [];
export const EMPTY_API_KEYS: ApiKeyRecord[] = [];

export const DEFAULT_FEATURE_FLAGS: FeatureFlagRecord[] = [];

export const DEFAULT_AI_ENGINE_CONFIG: AIEngineConfiguration = {
  simulateRateLimits: false,
  globalFallbackEnabled: true,
  strictSafetyGuard: true,
  maxTokensPerQuery: 2048,
  providers: {
    google_gemini: {
      id: 'google_gemini',
      name: 'Google Gemini',
      badge: 'Multimodal / High Throughput',
      enabled: true,
      apiKey: '••••••••••••••••••••••••••••••••',
      defaultModel: 'gemini-2.5-flash',
      availableModels: [
        'gemini-2.5-flash',
        'gemini-2.5-pro',
        'gemini-1.5-flash',
        'gemini-1.5-pro'
      ],
      status: 'healthy',
      lastLatencyMs: 142,
      lastTestedAt: '2026-08-22 10:40:12',
      quotaRemainingPercent: 94
    },
    anthropic_claude: {
      id: 'anthropic_claude',
      name: 'Anthropic Claude',
      badge: 'Deep Reasoning & Artifacts',
      enabled: true,
      apiKey: '••••••••••••••••••••••••••••••••',
      defaultModel: 'claude-3-7-sonnet-20250219',
      availableModels: [
        'claude-3-7-sonnet-20250219',
        'claude-3-5-sonnet-20241022',
        'claude-3-5-haiku-20241022'
      ],
      status: 'healthy',
      lastLatencyMs: 230,
      lastTestedAt: '2026-08-22 10:39:44',
      quotaRemainingPercent: 88
    },
    openai: {
      id: 'openai',
      name: 'OpenAI GPT',
      badge: 'Fast Translation & Structured JSON',
      enabled: true,
      apiKey: '••••••••••••••••••••••••••••••••',
      defaultModel: 'gpt-4o',
      availableModels: [
        'gpt-4o',
        'gpt-4o-mini',
        'o3-mini',
        'o1'
      ],
      status: 'healthy',
      lastLatencyMs: 185,
      lastTestedAt: '2026-08-22 10:38:21',
      quotaRemainingPercent: 91
    },
    deepseek: {
      id: 'deepseek',
      name: 'DeepSeek',
      badge: 'Deep Stacktrace Decompilation',
      enabled: true,
      apiKey: '••••••••••••••••••••••••••••••••',
      defaultModel: 'deepseek-reasoner',
      availableModels: [
        'deepseek-chat',
        'deepseek-reasoner'
      ],
      status: 'healthy',
      lastLatencyMs: 290,
      lastTestedAt: '2026-08-22 10:37:05',
      quotaRemainingPercent: 97
    },
    groq: {
      id: 'groq',
      name: 'Groq LPU',
      badge: 'Sub-tick Sub-50ms Inference',
      enabled: true,
      apiKey: '••••••••••••••••••••••••••••••••',
      defaultModel: 'llama-3.3-70b-versatile',
      availableModels: [
        'llama-3.3-70b-versatile',
        'mixtral-8x7b-32768',
        'llama-3.1-8b-instant'
      ],
      status: 'healthy',
      lastLatencyMs: 48,
      lastTestedAt: '2026-08-22 10:41:00',
      quotaRemainingPercent: 99
    },
    local_llm: {
      id: 'local_llm',
      name: 'Local LLM / Ollama',
      badge: 'Air-Gapped / Zero Cloud Cost',
      enabled: true,
      apiKey: 'none',
      baseUrl: 'http://localhost:11434/v1',
      defaultModel: 'llama3.2:latest',
      availableModels: [
        'llama3.2:latest',
        'mistral-nemo:latest',
        'qwen2.5-coder:14b',
        'deepseek-r1:8b'
      ],
      status: 'healthy',
      lastLatencyMs: 110,
      lastTestedAt: '2026-08-22 10:35:18',
      quotaRemainingPercent: 100
    }
  },
  taskAssignments: {
    ai_triage: {
      taskType: 'ai_triage',
      title: 'Crash Dumps & Log Post-Mortem Triage',
      description: 'Disassembles Java NullPointerExceptions, chunk memory leaks, and generates root-cause post-mortems.',
      primaryProvider: 'google_gemini',
      primaryModel: 'gemini-2.5-flash',
      fallbackProvider: 'deepseek',
      fallbackModel: 'deepseek-reasoner',
      autoFallbackOnRateLimit: true,
      timeoutMs: 4000
    },
    copilot: {
      taskType: 'copilot',
      title: 'UmbrellaDashboard Copilot & NL Cluster Ops',
      description: 'Conversational network diagnostics, dynamic CLI command generation, and operational health summaries.',
      primaryProvider: 'anthropic_claude',
      primaryModel: 'claude-3-7-sonnet-20250219',
      fallbackProvider: 'openai',
      fallbackModel: 'gpt-4o',
      autoFallbackOnRateLimit: true,
      timeoutMs: 5000
    },
    grim_combat: {
      taskType: 'grim_combat',
      title: 'GrimAC Sub-tick Packet Vector & False Positive AI',
      description: 'Analyzes reach vectors, movement packets, and rotation jitter to discern closet cheats from lag spikes.',
      primaryProvider: 'google_gemini',
      primaryModel: 'gemini-2.5-flash',
      fallbackProvider: 'groq',
      fallbackModel: 'llama-3.3-70b-versatile',
      autoFallbackOnRateLimit: true,
      timeoutMs: 2500
    },
    translation: {
      taskType: 'translation',
      title: 'Real-Time Player Chat Translation & Slur Filter',
      description: 'Bidirectional chat localization across 30+ languages with Minecraft gaming slang preservation.',
      primaryProvider: 'openai',
      primaryModel: 'gpt-4o-mini',
      fallbackProvider: 'google_gemini',
      fallbackModel: 'gemini-1.5-flash',
      autoFallbackOnRateLimit: true,
      timeoutMs: 1500
    },
    appeals: {
      taskType: 'appeals',
      title: 'Ban Appeal Sincerity & Sentiment Scoring',
      description: 'Evaluates player apology tone, past infraction volume, and predicts risk of re-offending.',
      primaryProvider: 'anthropic_claude',
      primaryModel: 'claude-3-5-sonnet-20241022',
      fallbackProvider: 'google_gemini',
      fallbackModel: 'gemini-2.5-flash',
      autoFallbackOnRateLimit: true,
      timeoutMs: 4500
    },
    tps_prediction: {
      taskType: 'tps_prediction',
      title: 'Autonomous TPS Forecasting & Watchdog GC Sweeper',
      description: 'Time-series forecasting over tick MSPT graphs to trigger preemptive non-blocking ZGC garbage collection.',
      primaryProvider: 'local_llm',
      primaryModel: 'llama3.2:latest',
      fallbackProvider: 'google_gemini',
      fallbackModel: 'gemini-2.5-flash',
      autoFallbackOnRateLimit: true,
      timeoutMs: 3000
    }
  }
};

