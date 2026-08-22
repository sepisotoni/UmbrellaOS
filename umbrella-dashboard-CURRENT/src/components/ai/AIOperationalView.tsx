import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import {
  Sparkles,
  Send,
  Flame,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Bot,
  User,
  Sliders,
  Cpu,
  Layers,
  FileText,
  Activity,
  Terminal
} from 'lucide-react';

export const AIOperationalView: React.FC = () => {
  const {
    copilotMessages,
    sendCopilotPrompt,
    crashReports,
    generatePostMortem,
    servers,
    addToast
  } = useDashboard();

  type AISection = 'copilot' | 'crashes' | 'postmortem' | 'model-router';
  const [activeSection, setActiveSection] = useState<AISection>('copilot');
  const [inputPrompt, setInputPrompt] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // Model router settings
  const [activeProvider, setActiveProvider] = useState<'gemini_flash' | 'anthropic_claude' | 'openrouter_deepseek'>('gemini_flash');
  const [strictSafetyGuard, setStrictSafetyGuard] = useState(true);
  const [maxTokensPerQuery, setMaxTokensPerQuery] = useState(2048);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPrompt.trim() || isTyping) return;

    const query = inputPrompt.trim();
    setInputPrompt('');
    setIsTyping(true);
    await sendCopilotPrompt(query);
    setIsTyping(false);
  };

  const samplePrompts = [
    "Why is any instance dropping TPS below 18?",
    "Check alt accounts and client brand for connected players",
    "Analyze recent combat violation patterns across proxy routes",
    "How many players are online on proxies?",
    "Recommend JVM memory flags for high player-count lobby nodes"
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight font-display">
                Operational Intelligence & AI Governance
              </h1>
              <p className="text-xs text-slate-400">
                Crash telemetry diagnosis, NL cluster queries, post-mortem generation, and LLM model routing
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-emerald-400 font-semibold">Gemini 2.5 Flash Active</span>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveSection('copilot')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'copilot'
              ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Bot className="h-3.5 w-3.5" />
          <span>Incident Copilot (Chat)</span>
        </button>

        <button
          onClick={() => setActiveSection('crashes')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'crashes'
              ? 'bg-slate-800 text-amber-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Flame className="h-3.5 w-3.5" />
          <span>Crash Dumps & Triage</span>
          <span className="font-mono text-[10px] bg-amber-950/80 text-amber-300 px-1.5 py-0.2 rounded border border-amber-500/30">
            {crashReports.length}
          </span>
        </button>

        <button
          onClick={() => setActiveSection('postmortem')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'postmortem'
              ? 'bg-slate-800 text-indigo-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Post-Mortem Generator</span>
        </button>

        <button
          onClick={() => setActiveSection('model-router')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'model-router'
              ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Sliders className="h-3.5 w-3.5" />
          <span>Model Router & Constitution</span>
        </button>
      </div>

      {/* Section 1: Copilot Chat */}
      {activeSection === 'copilot' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Chat Interface */}
          <div className="lg:col-span-3 flex flex-col h-[580px] rounded-xl border border-slate-800 bg-[#0c1017] shadow-lg overflow-hidden">
            {/* Message Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
              {copilotMessages.map(msg => {
                const isAssistant = msg.role === 'assistant';
                return (
                  <div 
                    key={msg.id}
                    className={`flex items-start gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}
                  >
                    <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                      isAssistant 
                        ? 'bg-cyan-950/60 border border-cyan-500/40 text-cyan-300' 
                        : 'bg-indigo-950/60 border border-indigo-500/40 text-indigo-300'
                    }`}>
                      {isAssistant ? <Sparkles className="h-4 w-4" /> : <User className="h-4 w-4" />}
                    </div>
                    <div className={`max-w-2xl rounded-xl p-4 leading-relaxed ${
                      isAssistant 
                        ? 'bg-slate-900/90 border border-slate-800 text-slate-200 shadow-sm' 
                        : 'bg-cyan-950/40 border border-cyan-500/30 text-white shadow-sm'
                    }`}>
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5 mb-2 font-mono text-[10px]">
                        <span className="font-bold text-slate-400">{isAssistant ? 'Umbrella AI Copilot' : 'Administrator'}</span>
                        <span className="text-slate-500">{msg.timestamp}</span>
                      </div>
                      <div className="whitespace-pre-wrap font-mono text-[12px] space-y-2">
                        {msg.content}
                      </div>
                    </div>
                  </div>
                );
              })}
              {isTyping && (
                <div className="flex items-center gap-2 text-xs text-cyan-400 font-mono italic">
                  <Sparkles className="h-3.5 w-3.5 animate-spin" />
                  <span>Umbrella AI is correlating server metrics and telemetry...</span>
                </div>
              )}
            </div>

            {/* Input form */}
            <form onSubmit={handleSend} className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center gap-2">
              <input
                type="text"
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                placeholder="Ask about TPS lag, player suspicion, crash dumps, or configs..."
                className="flex-1 rounded-xl border border-slate-700 bg-[#0c1017] px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
              />
              <button
                type="submit"
                disabled={!inputPrompt.trim() || isTyping}
                className="rounded-xl bg-cyan-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm font-mono"
              >
                <Send className="h-3.5 w-3.5" />
                <span>Ask</span>
              </button>
            </form>
          </div>

          {/* Right Sidebar: Sample Prompts & Cluster Insights */}
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-2.5">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Suggested Inquiries</h3>
              <div className="space-y-1.5">
                {samplePrompts.map(p => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => {
                      setInputPrompt(p);
                    }}
                    className="w-full text-left p-2 rounded-lg border border-slate-800 bg-slate-900/60 hover:border-cyan-500/40 text-[11px] text-slate-300 hover:text-cyan-200 transition-colors font-mono"
                  >
                    "{p}"
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-2 text-xs font-mono">
              <div className="font-bold text-white flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-emerald-400" />
                <span>Context Grounding</span>
              </div>
              <div className="text-[11px] text-slate-400 space-y-1">
                <p>• {servers.length} Instances streamed</p>
                <p>• Real-time GrimAC packet logs</p>
                <p>• Paper Watchdog tick timings</p>
                <p>• PostgreSQL replica state store</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Section 2: Crash Dumps & Triage */}
      {activeSection === 'crashes' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {crashReports.length === 0 ? (
              <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
                Zero crash dumps recorded. All JVM nodes reporting stable thread loops.
              </div>
            ) : (
              crashReports.map(crash => (
                <div
                  key={crash.id}
                  className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 shadow-sm"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm font-mono">{crash.serverName}</span>
                        <span className="font-mono text-[10px] text-slate-400">#{crash.id}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/40 text-rose-300 border border-rose-500/30">
                          {crash.severity}
                        </span>
                      </div>
                      <div className="text-xs text-rose-400 font-mono mt-1 font-semibold">
                        {crash.crashCause}
                      </div>
                    </div>
                    <span className="text-xs font-mono text-slate-500">{crash.timestamp}</span>
                  </div>

                  {/* Stack Trace Preview */}
                  <div>
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1 font-mono">Stack Trace Excerpt</div>
                    <pre className="p-3 rounded-lg border border-slate-800 bg-[#05070a] text-rose-300 font-mono text-[11px] overflow-x-auto">
                      {crash.stackTracePreview}
                    </pre>
                  </div>

                  {/* AI Diagnosis Card */}
                  <div className="rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-4 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-cyan-300 font-mono">
                      <Sparkles className="h-4 w-4 text-cyan-400" />
                      <span>Umbrella AI Automated Root Cause Analysis</span>
                    </div>
                    <p className="text-xs text-slate-200 font-mono leading-relaxed">
                      {crash.aiDiagnosis}
                    </p>
                    <div className="mt-2 pt-2 border-t border-cyan-950 flex items-center justify-between text-xs font-mono">
                      <span className="text-emerald-300">Suggested Fix: {crash.aiSuggestedFix}</span>
                      <button
                        onClick={() => {
                          addToast('success', 'Config Auto-Patched', `Applied recommended fix to ${crash.serverName}.`);
                        }}
                        className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors"
                      >
                        Apply 1-Click Patch
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800 font-mono">
                    <button
                      onClick={() => generatePostMortem(crash.id)}
                      className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-colors flex items-center gap-1.5"
                    >
                      <FileText className="h-3.5 w-3.5" />
                      <span>Generate Post-Mortem Report</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Section 3: Post-Mortem Generator */}
      {activeSection === 'postmortem' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-indigo-500/30 bg-[#0c1017] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-400" />
                <h3 className="text-sm font-bold text-white font-display">Automated Incident Post-Mortem Generator</h3>
              </div>
              <button
                onClick={() => {
                  generatePostMortem('CRASH-LIVE-TRIAGE');
                  addToast('info', 'Compiling SLA Report', 'Synthesizing stack trace delta and node uptime...');
                }}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors font-mono"
              >
                Compile Incident Report
              </button>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-[#05070a] font-mono text-xs text-slate-300 space-y-3 leading-relaxed">
              <div className="text-cyan-400 font-bold"># Incident Post-Mortem: Cluster Root Cause Analysis Engine</div>
              <div><strong>Status:</strong> Ready for incident ingestion. Trigger above or submit crash log from console view.</div>
              <div><strong>SLA Target:</strong> 99.95% Network Availability across Velocity + Game Cores.</div>
              <div className="border-t border-slate-800 pt-2 text-emerald-300">
                <strong>Standard Recovery Pipeline:</strong><br />
                1. Automatic Watchdog detection on unresponsive tick loop.<br />
                2. Instant memory freeze & snapshot delta creation.<br />
                3. Gemini GenAI stack trace disassembly and hotfix prescription.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Section 4: Model Router & Constitution */}
      {activeSection === 'model-router' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Gemini Flash */}
            <div
              onClick={() => setActiveProvider('gemini_flash')}
              className={`rounded-xl border p-4 cursor-pointer transition-all ${
                activeProvider === 'gemini_flash'
                  ? 'border-cyan-500/60 bg-cyan-950/20 shadow-md ring-1 ring-cyan-500/40'
                  : 'border-slate-800 bg-[#0c1017] hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-xs font-mono">Google Gemini 2.5 Flash</span>
                {activeProvider === 'gemini_flash' && <CheckCircle2 className="h-4 w-4 text-cyan-400" />}
              </div>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed font-mono">
                Ultra-low latency real-time log stream summarization and instant GrimAC anomaly verification.
              </p>
              <div className="mt-3 text-[10px] font-mono text-emerald-400">Default Primary Provider</div>
            </div>

            {/* Anthropic Claude */}
            <div
              onClick={() => setActiveProvider('anthropic_claude')}
              className={`rounded-xl border p-4 cursor-pointer transition-all ${
                activeProvider === 'anthropic_claude'
                  ? 'border-cyan-500/60 bg-cyan-950/20 shadow-md ring-1 ring-cyan-500/40'
                  : 'border-slate-800 bg-[#0c1017] hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-xs font-mono">Anthropic Claude 3.5 Sonnet</span>
                {activeProvider === 'anthropic_claude' && <CheckCircle2 className="h-4 w-4 text-cyan-400" />}
              </div>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed font-mono">
                Deep architectural analysis for Java JVM bytecode disassemblies, complex crash dumps, and appeal sentiment.
              </p>
              <div className="mt-3 text-[10px] font-mono text-slate-400">Fallback Tier 1</div>
            </div>

            {/* OpenRouter */}
            <div
              onClick={() => setActiveProvider('openrouter_deepseek')}
              className={`rounded-xl border p-4 cursor-pointer transition-all ${
                activeProvider === 'openrouter_deepseek'
                  ? 'border-cyan-500/60 bg-cyan-950/20 shadow-md ring-1 ring-cyan-500/40'
                  : 'border-slate-800 bg-[#0c1017] hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-xs font-mono">OpenRouter Multi-Gateway</span>
                {activeProvider === 'openrouter_deepseek' && <CheckCircle2 className="h-4 w-4 text-cyan-400" />}
              </div>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed font-mono">
                Redundant distributed gateway supporting DeepSeek R1, Llama 3.3 70B, and custom local Ollama models.
              </p>
              <div className="mt-3 text-[10px] font-mono text-slate-400">Fallback Tier 2</div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Constitution Safety & Rate Limits</h3>
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <div>
                  <div className="font-semibold text-white font-mono">Strict System Command Execution Guard</div>
                  <div className="text-[11px] text-slate-400 font-mono">Requires explicit human confirmation for destructive commands (`rm -rf`, `stop all`, `op`).</div>
                </div>
                <input
                  type="checkbox"
                  checked={strictSafetyGuard}
                  onChange={(e) => setStrictSafetyGuard(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-cyan-500"
                />
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <div>
                  <div className="font-semibold text-white font-mono">Max Output Tokens per Analysis</div>
                  <div className="text-[11px] text-slate-400 font-mono">Prevents unbounded context memory usage during large stack trace processing.</div>
                </div>
                <select
                  value={maxTokensPerQuery}
                  onChange={(e) => setMaxTokensPerQuery(Number(e.target.value))}
                  className="rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-white font-mono"
                >
                  <option value={1024}>1,024 Tokens</option>
                  <option value={2048}>2,048 Tokens</option>
                  <option value={4096}>4,096 Tokens</option>
                  <option value={8192}>8,192 Tokens</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
