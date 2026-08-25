/**
 * UmbrellaOS Settings — full rebuild
 * Fetches all settings from /api/v1/settings and saves per-key via PATCH.
 * Tabs: AI · Anticheat · Bridge · Discord · Moderation · RCON · Server · Sync · Visual
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot, Shield, MessageSquare, Hash, Gavel, Terminal,
  Server, RefreshCw, Palette, Save, Eye, EyeOff, Flag,
  CheckCircle, AlertCircle, Loader2, ChevronRight,
} from 'lucide-react';
import { api, SettingRecord } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import { BrandVisualSettings } from './BrandVisualSettings';
import { BrandShowcaseModal } from '../common/BrandShowcaseModal';
import { LogoRenderMode } from '../common/BrandLogos';

// ─── Tab definitions ──────────────────────────────────────────────────────────
type SettingsTab = 'ai' | 'anticheat' | 'bridge' | 'discord' | 'moderation' | 'rcon' | 'server' | 'sync' | 'visual';

const TABS: { id: SettingsTab; label: string; icon: React.ReactNode; desc: string }[] = [
  { id: 'ai',         label: 'AI Engine',    icon: <Bot className="h-4 w-4" />,            desc: 'API keys, model selection, provider toggles' },
  { id: 'anticheat',  label: 'Anticheat',    icon: <Shield className="h-4 w-4" />,          desc: 'GrimAC thresholds, auto-ban, AI review' },
  { id: 'bridge',     label: 'Chat Bridge',  icon: <MessageSquare className="h-4 w-4" />,   desc: 'MC ↔ Discord bidirectional chat relay' },
  { id: 'discord',    label: 'Discord',      icon: <Hash className="h-4 w-4" />,            desc: 'Bot token, guild ID, channels, OAuth2' },
  { id: 'moderation', label: 'Moderation',   icon: <Gavel className="h-4 w-4" />,           desc: 'Ban expiry checks, Discord link requirement' },
  { id: 'rcon',       label: 'RCON',         icon: <Terminal className="h-4 w-4" />,        desc: 'Minecraft RCON host, port, password' },
  { id: 'server',     label: 'Server',       icon: <Server className="h-4 w-4" />,          desc: 'Server name, player slots, control commands' },
  { id: 'sync',       label: 'Sync',         icon: <RefreshCw className="h-4 w-4" />,       desc: 'Heartbeat timeout, mute sync intervals' },
  { id: 'visual',     label: 'Visual',       icon: <Palette className="h-4 w-4" />,         desc: 'Dashboard appearance, logos, atmosphere' },
];

// ─── Field renderer ───────────────────────────────────────────────────────────
interface FieldProps {
  record: SettingRecord;
  value: string;
  onChange: (key: string, val: string) => void;
  saving: Record<string, boolean>;
  saved: Record<string, boolean>;
  errors: Record<string, string>;
  onSave: (key: string) => void;
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
              onChange(record.key, value === 'true' ? 'false' : 'true');
              setTimeout(() => onSave(record.key), 0);
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

// ─── Main ─────────────────────────────────────────────────────────────────────
export const SettingsView: React.FC = () => {
  const {
    addToast, setActiveTab,
    showDoodles, setShowDoodles,
    doodleOpacity, setDoodleOpacity,
    selectedBrand, setSelectedBrand,
  } = useDashboard();

  const [activeTab, setTab] = useState<SettingsTab>('ai');
  const [allSettings, setAllSettings] = useState<SettingRecord[]>([]);
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
      const records = await api.getSettings();
      setAllSettings(records);
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

  const handleSave = useCallback(async (key: string) => {
    const val = values[key];
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

  const tabRecords = activeTab === 'visual'
    ? []
    : allSettings.filter((r) => r.category === activeTab);

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
        {/* Sidebar nav */}
        <aside className="shrink-0 w-44 space-y-0.5">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`w-full flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-xs font-medium transition cursor-pointer ${
                activeTab === t.id
                  ? 'bg-indigo-600/20 border border-indigo-500/40 text-white'
                  : 'border border-transparent text-slate-400 hover:text-white hover:bg-[#060b1c]'
              }`}
            >
              <span className={activeTab === t.id ? 'text-indigo-400' : 'text-slate-500'}>{t.icon}</span>
              <span>{t.label}</span>
              {activeTab === t.id && <ChevronRight className="h-3 w-3 ml-auto text-indigo-400" />}
            </button>
          ))}
        </aside>

        {/* Content panel */}
        <div className="flex-1 min-w-0">
          <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 backdrop-blur-xl p-5">
            {/* Tab header */}
            {(() => {
              const t = TABS.find((x) => x.id === activeTab)!;
              return (
                <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[#141d3d]">
                  <div className="h-9 w-9 rounded-xl border border-indigo-500/30 bg-indigo-950/40 flex items-center justify-center text-indigo-400">
                    {t.icon}
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white">{t.label}</h2>
                    <p className="text-[11px] text-slate-400">{t.desc}</p>
                  </div>
                </div>
              );
            })()}

            {/* Visual tab is special — renders BrandVisualSettings */}
            {activeTab === 'visual' ? (
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
