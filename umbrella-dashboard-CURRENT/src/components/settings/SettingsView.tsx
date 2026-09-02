/**
 * UmbrellaOS Settings — full rebuild
 * Fetches all settings from /api/v1/settings and saves per-key via PATCH.
 * Two-column layout with categorized sidebar: Core, Integrations, Plugins, Appearance.
 * Tabs: AI Engine · AI Task Models · Anticheat · Server · Sync · RCON · Discord · Chat Bridge · Verification · Plugins (<server_id>) · Visual
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot, Cpu, Shield, MessageSquare, Hash, Gavel, Terminal,
  Server, RefreshCw, Palette, Save, Eye, EyeOff, Flag, Plus,
  CheckCircle, AlertCircle, Loader2, ChevronRight, Puzzle, Trash2
} from 'lucide-react';
import { api, SettingRecord, PluginHeartbeatStatus } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import { BrandVisualSettings } from './BrandVisualSettings';
import { BrandShowcaseModal } from '../common/BrandShowcaseModal';
import { LogoRenderMode } from '../common/BrandLogos';

// ─── Task Models Config ───────────────────────────────────────────────────────
interface TaskModelConfig {
  typeKey: string;
  label: string;
  description: string;
}

const TASK_TYPES: TaskModelConfig[] = [
  {
    typeKey: 'player_review',
    label: 'Player Anticheat Review',
    description: 'Autonomous evaluation of GrimAC violation telemetry and risk scoring.',
  },
  {
    typeKey: 'appeal_review',
    label: 'Appeal Review',
    description: 'AI recommendation & evidence validation for player ban/mute appeals.',
  },
  {
    typeKey: 'copilot',
    label: 'AI Copilot (/ask)',
    description: 'Natural-language operations, investigation assistant, and staff /ask query model.',
  },
  {
    typeKey: 'crash_risk',
    label: 'Crash Risk',
    description: 'Telemetry analysis for server crash detection, tick-rate anomaly forecasting.',
  },
];

// ─── Field renderer ───────────────────────────────────────────────────────────
interface FieldProps {
  record: SettingRecord;
  value: string;
  onChange: (key: string, val: string) => void;
  saving: Record<string, boolean>;
  saved: Record<string, boolean>;
  errors: Record<string, string>;
  onSave: (key: string, explicitValue?: string) => void;
}

const SettingsField: React.FC<FieldProps> = ({ record, value, onChange, saving, saved, errors, onSave }) => {
  const [masked, setMasked] = useState(true);

  const isBool = value === 'true' || value === 'false';
  const isNumber = !isBool && !isNaN(Number(value)) && value !== '';
  const isSaving = saving[record.key];
  const isSaved = saved[record.key];
  const error = errors[record.key];

  const inputClass =
    'w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2 text-sm text-white font-mono focus:border-indigo-500 focus:outline-none placeholder:text-slate-600';

  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/60 p-4 space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-indigo-300">{record.key}</span>
            {record.sensitive && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-700/40">SENSITIVE</span>
            )}
          </div>
          {record.description && (
            <p className="text-[11px] text-slate-400 mt-0.5">{record.description}</p>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {isSaving && <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin" />}
          {isSaved && !isSaving && <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />}
          {error && <AlertCircle className="h-3.5 w-3.5 text-rose-400" title={error} />}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {isBool ? (
          <button
            type="button"
            onClick={() => {
              const next = value === 'true' ? 'false' : 'true';
              onChange(record.key, next);
              // Pass the new value explicitly — onSave's closure may still
              // hold the pre-click value since React state hasn't committed yet.
              onSave(record.key, next);
            }}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
              value === 'true' ? 'bg-indigo-600' : 'bg-slate-700'
            }`}
          >
            <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
              value === 'true' ? 'translate-x-4' : 'translate-x-0.5'
            }`} />
          </button>
        ) : (
          <>
            <div className="relative flex-1">
              <input
                type={record.sensitive && masked ? 'password' : isNumber ? 'number' : 'text'}
                value={value}
                onChange={(e) => onChange(record.key, e.target.value)}
                onBlur={() => onSave(record.key)}
                onKeyDown={(e) => e.key === 'Enter' && onSave(record.key)}
                className={inputClass}
                placeholder={record.sensitive ? '••••••••' : 'Not set'}
              />
            </div>
            {record.sensitive && (
              <button
                type="button"
                onClick={() => setMasked((m) => !m)}
                className="shrink-0 text-slate-500 hover:text-slate-300 transition cursor-pointer"
              >
                {masked ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </button>
            )}
            <button
              type="button"
              onClick={() => onSave(record.key)}
              disabled={isSaving}
              className="shrink-0 inline-flex items-center gap-1 rounded-lg border border-indigo-500/40 bg-indigo-950/40 hover:bg-indigo-900/60 px-2.5 py-1.5 text-[11px] font-bold text-indigo-300 hover:text-white transition cursor-pointer disabled:opacity-50"
            >
              <Save className="h-3 w-3" />
              Save
            </button>
          </>
        )}
      </div>

      {error && <p className="text-[11px] text-rose-400 font-mono">{error}</p>}
    </div>
  );
};

// ─── AI Task Model Card ───────────────────────────────────────────────────────
interface TaskModelCardProps {
  config: TaskModelConfig;
  values: Record<string, string>;
  onChange: (key: string, val: string) => void;
  onSave: (key: string, explicitValue?: string) => Promise<void>;
  saving: Record<string, boolean>;
  saved: Record<string, boolean>;
}

const TaskModelCard: React.FC<TaskModelCardProps> = ({
  config,
  values,
  onChange,
  onSave,
  saving,
  saved,
}) => {
  const primaryKey = `ai.task.${config.typeKey}.primary_model`;
  const fb1Key = `ai.task.${config.typeKey}.fallback_model_1`;
  const fb2Key = `ai.task.${config.typeKey}.fallback_model_2`;
  const extraKey = `ai.task.${config.typeKey}.extra_fallback_models`;

  const primaryVal = values[primaryKey] ?? '';
  const fb1Val = values[fb1Key] ?? '';
  const fb2Val = values[fb2Key] ?? '';

  let extraList: string[] = [];
  try {
    const parsed = JSON.parse(values[extraKey] || '[]');
    if (Array.isArray(parsed)) extraList = parsed;
  } catch {
    extraList = [];
  }

  const [extras, setExtras] = useState<string[]>(extraList);

  useEffect(() => {
    try {
      const parsed = JSON.parse(values[extraKey] || '[]');
      if (Array.isArray(parsed)) setExtras(parsed);
    } catch {
      setExtras([]);
    }
  }, [values[extraKey]]);

  const handleAddExtra = () => {
    const updated = [...extras, ''];
    setExtras(updated);
    onChange(extraKey, JSON.stringify(updated));
  };

  const handleExtraChange = (index: number, val: string) => {
    const updated = [...extras];
    updated[index] = val;
    setExtras(updated);
    onChange(extraKey, JSON.stringify(updated));
  };

  const handleRemoveExtra = (index: number) => {
    const updated = extras.filter((_, i) => i !== index);
    setExtras(updated);
    onChange(extraKey, JSON.stringify(updated));
  };

  const handleSaveAll = async () => {
    await Promise.all([
      onSave(primaryKey),
      onSave(fb1Key),
      onSave(fb2Key),
      onSave(extraKey),
    ]);
  };

  const isCardSaving = saving[primaryKey] || saving[fb1Key] || saving[fb2Key] || saving[extraKey];
  const isCardSaved = saved[primaryKey] || saved[fb1Key] || saved[fb2Key] || saved[extraKey];

  const inputClass =
    'w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2 text-xs text-white font-mono focus:border-indigo-500 focus:outline-none placeholder:text-slate-600';

  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/80 p-5 space-y-4">
      <div className="flex items-start justify-between gap-4 border-b border-[#141d3d] pb-3">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Cpu className="h-4 w-4 text-indigo-400" />
            {config.label}
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">{config.description}</p>
        </div>
        <button
          type="button"
          onClick={handleSaveAll}
          disabled={isCardSaving}
          className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-950/60 hover:bg-indigo-900/80 px-3 py-1.5 text-xs font-bold text-indigo-200 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          {isCardSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
          <span>{isCardSaved ? 'Saved' : 'Save Task Models'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label className="block text-[11px] font-mono text-indigo-300 mb-1">Primary Model</label>
          <input
            type="text"
            value={primaryVal}
            onChange={(e) => onChange(primaryKey, e.target.value)}
            placeholder="e.g. openai/gpt-4o-mini"
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Fallback 1</label>
          <input
            type="text"
            value={fb1Val}
            onChange={(e) => onChange(fb1Key, e.target.value)}
            placeholder="e.g. anthropic/claude-3-5-haiku"
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Fallback 2</label>
          <input
            type="text"
            value={fb2Val}
            onChange={(e) => onChange(fb2Key, e.target.value)}
            placeholder="e.g. google/gemini-2.5-flash"
            className={inputClass}
          />
        </div>
      </div>

      {extras.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-[#141d3d]/60">
          <label className="block text-[11px] font-mono text-slate-400">Additional Fallback Chain</label>
          {extras.map((extra, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                value={extra}
                onChange={(e) => handleExtraChange(idx, e.target.value)}
                placeholder={`Fallback ${idx + 3} model ID`}
                className={inputClass}
              />
              <button
                type="button"
                onClick={() => handleRemoveExtra(idx)}
                className="text-slate-500 hover:text-rose-400 transition p-1.5"
                title="Remove fallback"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-start">
        <button
          type="button"
          onClick={handleAddExtra}
          className="inline-flex items-center gap-1 text-[11px] font-mono text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
        >
          <Plus className="h-3 w-3" />
          <span>+ Add fallback</span>
        </button>
      </div>
    </div>
  );
};

// ─── Main ─────────────────────────────────────────────────────────────────────
export const SettingsView: React.FC = () => {
  const {
    addToast, setActiveTab,
    showDoodles, setShowDoodles,
    doodleOpacity, setDoodleOpacity,
    selectedBrand, setSelectedBrand,
  } = useDashboard();

  const [activeTab, setTab] = useState<string>('ai');
  const [allSettings, setAllSettings] = useState<SettingRecord[]>([]);
  const [plugins, setPlugins] = useState<PluginHeartbeatStatus[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isBrandModalOpen, setIsBrandModalOpen] = useState(false);
  const [previewRenderMode, setPreviewRenderMode] = useState<LogoRenderMode>('vector');
  const [copiedHex, setCopiedHex] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const [records, pluginList] = await Promise.all([
        api.getSettings(),
        api.getPluginsHeartbeat(),
      ]);
      setAllSettings(records);
      setPlugins(pluginList || []);
      const map: Record<string, string> = {};
      for (const r of records) map[r.key] = r.value ?? '';
      setValues(map);
    } catch (err: any) {
      addToast({ type: 'error', title: 'Failed to load settings', message: err.message });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const handleChange = (key: string, val: string) => {
    setValues((prev) => ({ ...prev, [key]: val }));
    setSaved((prev) => ({ ...prev, [key]: false }));
  };

  const handleSave = useCallback(async (key: string, explicitValue?: string) => {
    // Use explicitValue when provided (e.g. from toggle buttons that update state
    // and call save in the same tick — the closure may still hold the pre-update
    // value). Falls back to values[key] for text fields where the user has
    // finished typing before save fires.
    const val = explicitValue !== undefined ? explicitValue : values[key];
    if (val === undefined) return;
    setSaving((prev) => ({ ...prev, [key]: true }));
    setErrors((prev) => { const n = { ...prev }; delete n[key]; return n; });
    try {
      await api.updateSetting(key, val);
      setSaved((prev) => ({ ...prev, [key]: true }));
      setTimeout(() => setSaved((prev) => ({ ...prev, [key]: false })), 2500);
    } catch (err: any) {
      setErrors((prev) => ({ ...prev, [key]: err.message || 'Save failed' }));
      addToast({ type: 'error', title: `Failed to save ${key}`, message: err.message });
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }));
    }
  }, [values, addToast]);

  const handleCopyColor = (hex: string, name: string) => {
    navigator.clipboard.writeText(hex);
    setCopiedHex(hex);
    addToast({ type: 'info', title: 'Color Copied', message: `${name} (${hex}) copied` });
    setTimeout(() => setCopiedHex(null), 2000);
  };

  // Determine active plugin if tab is a plugin tab
  const isPluginTab = activeTab.startsWith('plugin:');
  const activeServerId = isPluginTab ? activeTab.replace('plugin:', '') : null;
  const selectedPlugin = plugins.find((p) => p.server_id === activeServerId);

  const formatRelativeTime = (isoString?: string) => {
    if (!isoString) return 'Never';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diffSec < 10) return 'Just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    return `${Math.floor(diffSec / 3600)}h ago`;
  };

  const tabRecords = activeTab === 'visual' || activeTab === 'ai_task_models'
    ? []
    : isPluginTab
    ? allSettings.filter((r) => r.category === `plugins.${activeServerId}` || r.key.startsWith(`plugins.${activeServerId}.`))
    : allSettings.filter((r) => r.category === activeTab);

  const sidebarBtnClass = (id: string) =>
    `w-full flex items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs font-medium transition cursor-pointer ${
      activeTab === id
        ? 'bg-indigo-600/20 border border-indigo-500/40 text-white'
        : 'border border-transparent text-slate-400 hover:text-white hover:bg-[#060b1c]'
    }`;

  return (
    <div id="umbrella-settings-view" className="space-y-5">
      <DisconnectedBanner />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">System Settings</h1>
          <p className="text-xs text-slate-400 mt-1">
            All changes save immediately per field — no global save required.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadSettings}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Reload
          </button>
          <button
            onClick={() => setActiveTab('feature-flags')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs font-medium text-indigo-300 hover:text-white transition cursor-pointer"
          >
            <Flag className="h-3.5 w-3.5" /> Feature Flags
          </button>
        </div>
      </div>

      <div className="flex gap-5">
        {/* Left Sidebar (fixed ~200px wide, categorized) */}
        <aside className="shrink-0 w-52 space-y-1 max-h-[calc(100vh-200px)] overflow-y-auto pr-1">
          {/* CORE SECTION */}
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest px-3 py-1 mt-1">
            CORE
          </div>
          {[
            { id: 'ai', label: 'AI Engine', icon: <Bot className="h-3.5 w-3.5" /> },
            { id: 'ai_task_models', label: 'AI Task Models', icon: <Cpu className="h-3.5 w-3.5" /> },
            { id: 'anticheat', label: 'Anticheat', icon: <Shield className="h-3.5 w-3.5" /> },
            { id: 'server', label: 'Server', icon: <Server className="h-3.5 w-3.5" /> },
            { id: 'sync', label: 'Sync', icon: <RefreshCw className="h-3.5 w-3.5" /> },
            { id: 'rcon', label: 'RCON', icon: <Terminal className="h-3.5 w-3.5" /> },
          ].map((item) => (
            <button key={item.id} onClick={() => setTab(item.id)} className={sidebarBtnClass(item.id)}>
              <span className={activeTab === item.id ? 'text-indigo-400' : 'text-slate-500'}>{item.icon}</span>
              <span>{item.label}</span>
              {activeTab === item.id && <ChevronRight className="h-3 w-3 ml-auto text-indigo-400" />}
            </button>
          ))}

          {/* INTEGRATIONS SECTION */}
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest px-3 py-1 mt-3">
            INTEGRATIONS
          </div>
          {[
            { id: 'discord', label: 'Discord', icon: <Hash className="h-3.5 w-3.5" /> },
            { id: 'bridge', label: 'Chat Bridge', icon: <MessageSquare className="h-3.5 w-3.5" /> },
            { id: 'verification', label: 'Verification', icon: <CheckCircle className="h-3.5 w-3.5" /> },
            { id: 'moderation', label: 'Moderation', icon: <Gavel className="h-3.5 w-3.5" /> },
          ].map((item) => (
            <button key={item.id} onClick={() => setTab(item.id)} className={sidebarBtnClass(item.id)}>
              <span className={activeTab === item.id ? 'text-indigo-400' : 'text-slate-500'}>{item.icon}</span>
              <span>{item.label}</span>
              {activeTab === item.id && <ChevronRight className="h-3 w-3 ml-auto text-indigo-400" />}
            </button>
          ))}

          {/* PLUGINS SECTION */}
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest px-3 py-1 mt-3">
            PLUGINS
          </div>
          {plugins.length === 0 ? (
            <div className="px-3 py-1 text-[11px] text-slate-600 italic">No plugins reported</div>
          ) : (
            plugins.map((p) => {
              const serverId = p.server_id;
              const tabId = `plugin:${serverId}`;
              const isSelected = activeTab === tabId;
              return (
                <button
                  key={tabId}
                  onClick={() => setTab(tabId)}
                  className={`w-full flex items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-medium transition cursor-pointer truncate ${
                    isSelected
                      ? 'bg-indigo-600/20 border border-indigo-500/40 text-white'
                      : 'border border-transparent text-slate-400 hover:text-white hover:bg-[#060b1c]'
                  }`}
                >
                  <Puzzle className={`h-3.5 w-3.5 shrink-0 ${isSelected ? 'text-indigo-400' : 'text-slate-500'}`} />
                  <span className="truncate">{p.server_name || p.server_id || 'Server Plugin'}</span>
                  {isSelected && <ChevronRight className="h-3 w-3 ml-auto text-indigo-400 shrink-0" />}
                </button>
              );
            })
          )}

          {/* APPEARANCE SECTION */}
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest px-3 py-1 mt-3">
            APPEARANCE
          </div>
          <button onClick={() => setTab('visual')} className={sidebarBtnClass('visual')}>
            <span className={activeTab === 'visual' ? 'text-indigo-400' : 'text-slate-500'}>
              <Palette className="h-3.5 w-3.5" />
            </span>
            <span>Visual</span>
            {activeTab === 'visual' && <ChevronRight className="h-3 w-3 ml-auto text-indigo-400" />}
          </button>
        </aside>

        {/* Content panel */}
        <div className="flex-1 min-w-0">
          <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 backdrop-blur-xl p-5">
            {/* Tab header */}
            {(() => {
              let title = activeTab.toUpperCase();
              let desc = 'Configure system parameters and behavior.';
              if (activeTab === 'ai') { title = 'AI Engine'; desc = 'API keys, provider enablement toggles, and default LLM configuration.'; }
              else if (activeTab === 'ai_task_models') { title = 'AI Task Models'; desc = 'Multi-provider model routing and failover chains for each automated intelligence workflow.'; }
              else if (activeTab === 'anticheat') { title = 'Anticheat Integration'; desc = 'GrimAC thresholds, automated punishment enforcement, and heuristic rules.'; }
              else if (activeTab === 'server') { title = 'Server Configuration'; desc = 'Network name, player caps, control commands, and server parameters.'; }
              else if (activeTab === 'sync') { title = 'Heartbeat & Sync'; desc = 'State synchronization cadence, heartbeat timeouts, and cache invalidation.'; }
              else if (activeTab === 'rcon') { title = 'RCON Access'; desc = 'Minecraft remote console connection hosts, ports, and credentials.'; }
              else if (activeTab === 'discord') { title = 'Discord Integration'; desc = 'Bot credentials, guild association, alerting channels, and OAuth2 parameters.'; }
              else if (activeTab === 'bridge') { title = 'Chat Bridge'; desc = 'Bidirectional Minecraft <-> Discord chat relay rules and formatting.'; }
              else if (activeTab === 'verification') { title = 'Player Verification'; desc = 'Account link requirements, verification codes, and Discord role assignment.'; }
              else if (activeTab === 'moderation') { title = 'Moderation Rules'; desc = 'Ban lifecycle, automated expiry sweeps, and punishment requirements.'; }
              else if (activeTab === 'visual') { title = 'Visual Appearance'; desc = 'Dashboard aesthetics, brand assets, wallpaper doodles, and color tokens.'; }
              else if (isPluginTab) { title = `Plugin: ${selectedPlugin?.name || activeServerId}`; desc = `Node settings and runtime status for ${selectedPlugin?.server || activeServerId}.`; }

              return (
                <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[#141d3d]">
                  <div className="h-9 w-9 rounded-xl border border-indigo-500/30 bg-indigo-950/40 flex items-center justify-center text-indigo-400">
                    {activeTab === 'ai_task_models' ? <Cpu className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white">{title}</h2>
                    <p className="text-[11px] text-slate-400">{desc}</p>
                  </div>
                </div>
              );
            })()}

            {/* AI Task Models Tab */}
            {activeTab === 'ai_task_models' ? (
              <div className="space-y-4">
                {TASK_TYPES.map((cfg) => (
                  <TaskModelCard
                    key={cfg.typeKey}
                    config={cfg}
                    values={values}
                    onChange={handleChange}
                    onSave={handleSave}
                    saving={saving}
                    saved={saved}
                  />
                ))}
              </div>
            ) : isPluginTab ? (
              <div className="space-y-5">
                {/* Read-only Plugin Telemetry Card */}
                <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/60 p-4 space-y-3">
                  <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider">Plugin Runtime Status</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-2.5">
                      <div className="text-[10px] text-slate-500 uppercase">Server Name</div>
                      <div className="text-white font-bold mt-0.5 truncate">{selectedPlugin?.server || selectedPlugin?.name || activeServerId}</div>
                    </div>
                    <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-2.5">
                      <div className="text-[10px] text-slate-500 uppercase">Umbrella Version</div>
                      <div className="text-indigo-300 font-bold mt-0.5">{selectedPlugin?.version || '1.0.0'}</div>
                    </div>
                    <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-2.5">
                      <div className="text-[10px] text-slate-500 uppercase">GrimAC Status</div>
                      <div className="mt-0.5">
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/40">
                          CONNECTED
                        </span>
                      </div>
                    </div>
                    <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-2.5">
                      <div className="text-[10px] text-slate-500 uppercase">Last Heartbeat</div>
                      <div className="text-slate-300 mt-0.5">{formatRelativeTime(selectedPlugin?.lastSeen)}</div>
                    </div>
                  </div>
                </div>

                {/* Plugin Specific Settings */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider">Plugin Specific Settings</h3>
                  {tabRecords.length === 0 ? (
                    <p className="text-xs text-slate-500 py-4 italic">No custom plugin configuration keys found for this server node.</p>
                  ) : (
                    tabRecords.map((record) => (
                      <SettingsField
                        key={record.key}
                        record={record}
                        value={values[record.key] ?? ''}
                        onChange={handleChange}
                        saving={saving}
                        saved={saved}
                        errors={errors}
                        onSave={handleSave}
                      />
                    ))
                  )}
                </div>
              </div>
            ) : activeTab === 'visual' ? (
              <div className="space-y-4">
                <BrandVisualSettings
                  showDoodles={showDoodles}
                  setShowDoodles={setShowDoodles}
                  doodleOpacity={doodleOpacity}
                  setDoodleOpacity={setDoodleOpacity}
                  selectedBrand={selectedBrand}
                  setSelectedBrand={setSelectedBrand}
                  previewRenderMode={previewRenderMode}
                  setPreviewRenderMode={setPreviewRenderMode}
                  onOpenBrandModal={() => setIsBrandModalOpen(true)}
                  copiedHex={copiedHex}
                  onCopyColor={handleCopyColor}
                />
              </div>
            ) : activeTab === 'verification' ? (
              <div className="space-y-4">
                {/* ── Master Toggle ── */}
                <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/60 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-indigo-400" />
                        <span className="text-sm font-bold text-white">Verification System</span>
                        {saving['verification.enabled'] && <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin" />}
                        {saved['verification.enabled'] && !saving['verification.enabled'] && <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Master toggle — when off, all verification commands and link flows are disabled server-wide.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={async () => {
                        const next = values['verification.enabled'] === 'true' ? 'false' : 'true';
                        handleChange('verification.enabled', next);
                        // Pass the new value explicitly so handleSave doesn't read the stale closure.
                        await handleSave('verification.enabled', next);
                      }}
                      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors cursor-pointer ${
                        values['verification.enabled'] === 'true' ? 'bg-indigo-600' : 'bg-slate-700'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                        values['verification.enabled'] === 'true' ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                </div>

                {/* ── Other verification settings ── */}
                {loading ? (
                  <div className="flex items-center justify-center py-10 text-slate-500 gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span className="text-sm">Loading…</span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {tabRecords.filter(r => r.key !== 'verification.enabled').map((record) => (
                      <SettingsField
                        key={record.key}
                        record={record}
                        value={values[record.key] ?? ''}
                        onChange={handleChange}
                        saving={saving}
                        saved={saved}
                        errors={errors}
                        onSave={handleSave}
                      />
                    ))}
                  </div>
                )}
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-16 text-slate-500 gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Loading settings from Core…</span>
              </div>
            ) : tabRecords.length === 0 ? (
              <p className="text-sm text-slate-500 py-10 text-center">No settings in this category.</p>
            ) : (
              <div className="space-y-3">
                {tabRecords.map((record) => (
                  <SettingsField
                    key={record.key}
                    record={record}
                    value={values[record.key] ?? ''}
                    onChange={handleChange}
                    saving={saving}
                    saved={saved}
                    errors={errors}
                    onSave={handleSave}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <BrandShowcaseModal
        isOpen={isBrandModalOpen}
        onClose={() => setIsBrandModalOpen(false)}
        selectedBrand={selectedBrand}
        onSelectBrand={setSelectedBrand}
        doodleOpacity={doodleOpacity}
        onDoodleOpacityChange={setDoodleOpacity}
        showDoodles={showDoodles}
        onToggleDoodles={setShowDoodles}
      />
    </div>
  );
};

export default SettingsView;
