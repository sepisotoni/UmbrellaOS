/**
 * UmbrellaOS Settings Module Types
 * Structured interfaces for network configuration, Discord parameters, and AI heuristics.
 */

import { BrandLogoVariant, LogoRenderMode } from '../common/BrandLogos';

export interface SettingsFormData {
  coreUrl: string;
  adminKey: string;
  discordInvite: string;
  discordInviteTarget: '_blank' | '_self';
  discordGuildId: string;
  discordChannelId: string;
  verificationTemplate: string;
  greeterTemplate: string;
  appealRedirectTemplate: string;
  aiModel: string;
  aiTemperature: number;
}

export interface BrandVisualConfig {
  showDoodles: boolean;
  doodleOpacity: number;
  selectedBrand: BrandLogoVariant;
  previewRenderMode: LogoRenderMode;
}
