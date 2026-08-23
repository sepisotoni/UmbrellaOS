import React, { useState, useEffect } from 'react';
import { api, NetworkSettings } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Settings,
  Server,
  Bot,
  MessageSquare,
  Sparkles,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
  Flag,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const { addToast, setActiveTab, checkHealth, isDisconnected } = useDashboard();
  const [coreUrl, setCoreUrl] = useState<string>(
    (import.meta as any).env?.VITE_UMBRELLA_CORE_URL || 'https://umbrellaos-core.onrender.com'
  );
  const [adminKey, setAdminKey] = useState<string>('');
  const [discordBotToken, setDiscordBotToken] = useState<string>('••••••••••••••••••••••••••••••••');
  const [discordGuildId, setDiscordGuildId] = useState<string>('');
  const [discordChannelId, setDiscordChannelId] = useState<string>('');
  const [verificationTemplate, setVerificationTemplate] = useState<string>(
    'Welcome {player}! Use `/verify code:{code}` on our Discord to link your account.'
  );
  const [greeterTemplate, setGreeterTemplate] = useState<string>(
    'Welcome {player} to the UmbrellaOS network!'
  );
  const [aiModel, setAiModel] = useState<string>('gemini-1.5-pro');
  const [aiTemperature, setAiTemperature] = useState<number>(0.2);

  const [isTestingAI, setIsTestingAI] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    api.getSettings().then((res: any) => {
      if (Array.isArray(res)) {
        const map = Object.fromEntries(res.map((r: any) => [r.key, r.value]));
        if (map.discord_guild_id) setDiscordGuildId(map.discord_guild_id);
        if (map.verification_channel_id) setDiscordChannelId(map.verification_channel_id);
        if (map.ai_model) setAiModel(map.ai_model);
      } else if (res && typeof res === 'object') {
        if (res.discord_guild_id) setDiscordGuildId(res.discord_guild_id);
        if (res.verification_channel_id) setDiscordChannelId(res.verification_channel_id);
        if (res.ai_model) setAiModel(res.ai_model);
      }
    }).catch(() => {});
  }, []);

  const handleTestAI = async () => {
    setIsTestingAI(true);
    try {
      const res = await api.askCopilot('System health diagnostic test. Reply with status.', {});
      addToast({
        type: 'success',
        title: 'AI Pipeline Verified',
        message: 'FastAPI Gemini AI bridge is operational.',
      });
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'AI Test Failed',
        message: err.message || '503 Service Unavailable or API key unset.',
      });
    } finally {
      setIsTestingAI(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      if (adminKey.trim()) {
        api.setAdminKey(adminKey.trim());
      }
      await api.updateSettings({
        discord_guild_id: discordGuildId.trim() || undefined,
        verification_channel_id: discordChannelId.trim() || undefined,
        ai_model: aiModel,
      });
      await checkHealth();
      addToast({
        type: 'success',
        title: 'Configuration Saved',
        message: 'Network parameters updated successfully.',
      });
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Save Failed',
        message: err.message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div id="umbrella-settings-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Network Configuration & System Settings</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Core FastAPI connection, Discord bot parameters, messaging templates, and AI engine setup.
          </p>
        </div>

        <button
          onClick={() => setActiveTab('feature-flags')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-purple-300 hover:text-white transition cursor-pointer"
        >
          <Flag className="h-3.5 w-3.5" />
          <span>Manage Feature Flags</span>
        </button>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6 font-mono text-xs">
        {/* Section 1: Core Connection */}
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1e1b4b] pb-3">
            <Server className="h-4 w-4 text-purple-400" />
            <h2 className="font-bold text-white uppercase text-sm font-sans">Core Connection & Gateway</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 mb-1">FastAPI Backend Endpoint</label>
              <input
                type="text"
                value={coreUrl}
                disabled
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-slate-400 cursor-not-allowed opacity-80"
              />
              <p className="text-[10px] text-slate-500 mt-1">Configured via VITE_UMBRELLA_CORE_URL</p>
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Admin API Key (X-Admin-Key)</label>
              <input
                type="password"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                placeholder="Enter secret admin key to override session..."
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Discord Bot Integration */}
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1e1b4b] pb-3">
            <Bot className="h-4 w-4 text-[#5865F2]" />
            <h2 className="font-bold text-white uppercase text-sm font-sans">Discord Integration & Verification</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 mb-1">Discord Guild ID</label>
              <input
                type="text"
                value={discordGuildId}
                onChange={(e) => setDiscordGuildId(e.target.value)}
                placeholder="e.g. 109283746581928374"
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Verification Channel ID</label>
              <input
                type="text"
                value={discordChannelId}
                onChange={(e) => setDiscordChannelId(e.target.value)}
                placeholder="e.g. 109283746581928375"
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Section 3: In-Game Messaging Templates */}
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1e1b4b] pb-3">
            <MessageSquare className="h-4 w-4 text-emerald-400" />
            <h2 className="font-bold text-white uppercase text-sm font-sans">Messaging & Announcement Templates</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-slate-300 mb-1">Verification Prompt Message</label>
              <input
                type="text"
                value={verificationTemplate}
                onChange={(e) => setVerificationTemplate(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Player Join Greeter Message</label>
              <input
                type="text"
                value={greeterTemplate}
                onChange={(e) => setGreeterTemplate(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Section 4: AI Model Selection & Test */}
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-400" />
              <h2 className="font-bold text-white uppercase text-sm font-sans">AI Model & Heuristics Engine</h2>
            </div>

            <button
              type="button"
              onClick={handleTestAI}
              disabled={isTestingAI}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-purple-500/40 bg-purple-950/40 hover:bg-purple-900/60 text-purple-300 text-xs font-bold transition cursor-pointer disabled:opacity-50"
            >
              <Sparkles className={`h-3 w-3 ${isTestingAI ? 'animate-spin' : ''}`} />
              <span>{isTestingAI ? 'Testing API...' : 'Test AI Connection'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 mb-1">Gemini Model Selector</label>
              <select
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none cursor-pointer"
              >
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Recommended for Complex Appeals)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash (Fast Heuristic Triage)</option>
                <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Experimental)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Temperature ({aiTemperature})</label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={aiTemperature}
                onChange={(e) => setAiTemperature(Number(e.target.value))}
                className="w-full mt-2 accent-purple-500 cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-xl border border-purple-500/50 bg-purple-600 hover:bg-purple-500 px-6 py-2.5 text-xs font-bold text-white transition shadow-[0_0_15px_rgba(168,85,247,0.3)] disabled:opacity-50 cursor-pointer"
          >
            <Save className="h-4 w-4" />
            <span>{isSaving ? 'Applying Settings...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
