/**
 * UmbrellaOS Main Settings View
 * Orchestrates network configuration, Discord integration, wallpaper atmosphere, templates, and AI heuristics.
 *
 * Modular Architecture:
 * - BrandVisualSettings: Wallpaper doodles and brand emblems suite.
 * - CoreGatewaySettings: FastAPI backend endpoint & X-Admin-Key.
 * - DiscordIntegrationSettings: Guild ID, verification channel, $discord_invite routing.
 * - MessagingTemplatesSettings: In-game prompt & greeter text templates.
 * - AIEngineSettings: Gemini model selection & temperature.
 */

import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import { LogoRenderMode } from '../common/BrandLogos';
import { BrandShowcaseModal } from '../common/BrandShowcaseModal';
import { BrandVisualSettings } from './BrandVisualSettings';
import { CoreGatewaySettings } from './CoreGatewaySettings';
import { DiscordIntegrationSettings } from './DiscordIntegrationSettings';
import { MessagingTemplatesSettings } from './MessagingTemplatesSettings';
import { AIEngineSettings } from './AIEngineSettings';
import { Flag, Save } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const {
    addToast,
    setActiveTab,
    checkHealth,
    showDoodles,
    setShowDoodles,
    doodleOpacity,
    setDoodleOpacity,
    selectedBrand,
    setSelectedBrand,
    discordInvite,
    setDiscordInvite,
  } = useDashboard();

  // Core & Auth State
  const [coreUrl] = useState<string>(
    (import.meta as any).env?.VITE_UMBRELLA_CORE_URL || 'https://umbrellaos-core.onrender.com'
  );
  const [adminKey, setAdminKey] = useState<string>('');

  // Discord State
  const [discordInviteInput, setDiscordInviteInput] = useState<string>(
    discordInvite || 'https://discord.gg/umbrella'
  );
  const [discordGuildId, setDiscordGuildId] = useState<string>('');
  const [discordChannelId, setDiscordChannelId] = useState<string>('');

  // Template State
  const [verificationTemplate, setVerificationTemplate] = useState<string>(
    'Welcome {player}! Use `/verify code:{code}` on our Discord to link your account.'
  );
  const [greeterTemplate, setGreeterTemplate] = useState<string>(
    'Welcome {player} to the UmbrellaOS network!'
  );

  // AI Heuristics State
  const [aiModel, setAiModel] = useState<string>('gemini-1.5-pro');
  const [aiTemperature, setAiTemperature] = useState<number>(0.2);

  // UI & Loading States
  const [isTestingAI, setIsTestingAI] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [previewRenderMode, setPreviewRenderMode] = useState<LogoRenderMode>('vector');
  const [isBrandModalOpen, setIsBrandModalOpen] = useState<boolean>(false);
  const [copiedHex, setCopiedHex] = useState<string | null>(null);

  // Hydrate settings from Core API on mount
  useEffect(() => {
    api
      .getSettings()
      .then((res: any) => {
        if (Array.isArray(res)) {
          const map = Object.fromEntries(res.map((r: any) => [r.key, r.value]));
          if (map.discord_guild_id) setDiscordGuildId(map.discord_guild_id);
          if (map.verification_channel_id) setDiscordChannelId(map.verification_channel_id);
          if (map.ai_model) setAiModel(map.ai_model);
          if (map.discord_invite) {
            setDiscordInviteInput(map.discord_invite);
            setDiscordInvite(map.discord_invite);
          }
        } else if (res && typeof res === 'object') {
          if (res.discord_guild_id) setDiscordGuildId(res.discord_guild_id);
          if (res.verification_channel_id) setDiscordChannelId(res.verification_channel_id);
          if (res.ai_model) setAiModel(res.ai_model);
          if (res.discord_invite) {
            setDiscordInviteInput(res.discord_invite);
            setDiscordInvite(res.discord_invite);
          }
        }
      })
      .catch(() => {});
  }, [setDiscordInvite]);

  // AI Diagnostic Pipeline Test
  const handleTestAI = async () => {
    setIsTestingAI(true);
    try {
      await api.askCopilot('System health diagnostic test. Reply with status.', {});
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

  // Palette color copy helper
  const handleCopyColor = (hex: string, name: string) => {
    navigator.clipboard.writeText(hex);
    setCopiedHex(hex);
    addToast({
      type: 'info',
      title: 'Color Copied',
      message: `${name} (${hex}) copied to clipboard`,
    });
    setTimeout(() => setCopiedHex(null), 2000);
  };

  // Submit all settings to Core
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      if (adminKey.trim()) {
        api.setAdminKey(adminKey.trim());
      }
      if (discordInviteInput.trim()) {
        setDiscordInvite(discordInviteInput.trim());
      }
      await api.updateSettings({
        discord_guild_id: discordGuildId.trim() || undefined,
        verification_channel_id: discordChannelId.trim() || undefined,
        ai_model: aiModel,
        discord_invite: discordInviteInput.trim() || undefined,
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
            Core FastAPI connection, Discord bot parameters, visuals & wallpaper, templates, and AI engine setup.
          </p>
        </div>

        <button
          onClick={() => setActiveTab('feature-flags')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs font-medium text-indigo-300 hover:text-white transition cursor-pointer"
        >
          <Flag className="h-3.5 w-3.5" />
          <span>Manage Feature Flags</span>
        </button>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Section 1: Visual Atmosphere, Wallpaper & Brand Logos Suite */}
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

        {/* Section 2: Core Connection & Secret Key */}
        <CoreGatewaySettings
          coreUrl={coreUrl}
          adminKey={adminKey}
          setAdminKey={setAdminKey}
        />

        {/* Section 3: Discord Bot Integration & $discord_invite Routing */}
        <DiscordIntegrationSettings
          discordGuildId={discordGuildId}
          setDiscordGuildId={setDiscordGuildId}
          discordChannelId={discordChannelId}
          setDiscordChannelId={setDiscordChannelId}
          discordInvite={discordInviteInput}
          setDiscordInvite={setDiscordInviteInput}
        />

        {/* Section 4: In-Game Messaging Templates */}
        <MessagingTemplatesSettings
          verificationTemplate={verificationTemplate}
          setVerificationTemplate={setVerificationTemplate}
          greeterTemplate={greeterTemplate}
          setGreeterTemplate={setGreeterTemplate}
        />

        {/* Section 5: AI Model Selection & Heuristics Diagnostic */}
        <AIEngineSettings
          aiModel={aiModel}
          setAiModel={setAiModel}
          aiTemperature={aiTemperature}
          setAiTemperature={setAiTemperature}
          isTestingAI={isTestingAI}
          onTestAI={handleTestAI}
        />

        {/* Save Actions Bar */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-600 hover:bg-indigo-500 px-6 py-2.5 text-xs font-bold text-white transition shadow-[0_0_15px_rgba(99,102,241,0.3)] disabled:opacity-50 cursor-pointer font-sans"
          >
            <Save className="h-4 w-4" />
            <span>{isSaving ? 'Applying Settings...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>

      {/* Brand Logos Showcase & SVG Code Export Modal */}
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
