/**
 * BrandVisualSettings Subcomponent
 * Manages atmospheric heaven starscape wallpaper, WhatsApp-style doodle overlay, and brand emblem suite.
 */

import React from 'react';
import { Palette, Eye, Sparkles, Check, Code2, Image as ImageIcon } from 'lucide-react';
import {
  BrandLogo,
  BrandLogoVariant,
  LogoRenderMode,
  BRAND_DEFINITIONS,
} from '../common/BrandLogos';

interface BrandVisualSettingsProps {
  showDoodles: boolean;
  setShowDoodles: (show: boolean) => void;
  doodleOpacity: number;
  setDoodleOpacity: (opacity: number) => void;
  selectedBrand: BrandLogoVariant;
  setSelectedBrand: (brand: BrandLogoVariant) => void;
  previewRenderMode: LogoRenderMode;
  setPreviewRenderMode: (mode: LogoRenderMode) => void;
  onOpenBrandModal: () => void;
  copiedHex: string | null;
  onCopyColor: (hex: string, name: string) => void;
}

const BRAND_PALETTES = [
  { name: 'Indigo Core', hex: '#6366f1', bg: 'bg-[#6366f1]' },
  { name: 'Cyan Pulse', hex: '#06b6d4', bg: 'bg-[#06b6d4]' },
  { name: 'Purple Bot', hex: '#a855f7', bg: 'bg-[#a855f7]' },
  { name: 'Sky Radar', hex: '#38bdf8', bg: 'bg-[#38bdf8]' },
];

export const BrandVisualSettings: React.FC<BrandVisualSettingsProps> = ({
  showDoodles,
  setShowDoodles,
  doodleOpacity,
  setDoodleOpacity,
  selectedBrand,
  setSelectedBrand,
  previewRenderMode,
  setPreviewRenderMode,
  onOpenBrandModal,
  copiedHex,
  onCopyColor,
}) => {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-[#141d3d] pb-3">
        <div className="flex items-center gap-2">
          <Palette className="h-4 w-4 text-indigo-400" />
          <h2 className="font-bold text-white uppercase text-sm font-sans">
            Brand Logos & Atmospheric Wallpaper
          </h2>
        </div>

        <button
          type="button"
          onClick={onOpenBrandModal}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-indigo-500/40 bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-300 text-xs font-bold transition cursor-pointer"
        >
          <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
          <span>Open Full Asset & SVG Export Suite</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono text-xs">
        {/* 1. Wallpaper Controls */}
        <div className="space-y-4 rounded-xl border border-[#141d3d]/70 bg-[#02040a] p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-indigo-400" />
              <span className="font-bold text-white font-sans text-xs">
                Heaven Cloud Night Sky Wallpaper
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={showDoodles}
                onChange={(e) => setShowDoodles(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
            </label>
          </div>

          <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
            Renders a subtle WhatsApp-style scrambled pattern with Minecraft telemetry, server terminal doodles, and night sky stars in the background.
          </p>

          <div>
            <div className="flex justify-between items-center text-[11px] text-slate-300 mb-1">
              <span>Doodle Intensity / Opacity</span>
              <span className="text-indigo-300 font-bold">{Math.round(doodleOpacity * 100)}%</span>
            </div>
            <input
              type="range"
              min={0.01}
              max={0.25}
              step={0.01}
              value={doodleOpacity}
              disabled={!showDoodles}
              onChange={(e) => setDoodleOpacity(parseFloat(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer disabled:opacity-30"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>Subtle (2%)</span>
              <span>Default (8%)</span>
              <span>High Contrast (25%)</span>
            </div>
          </div>
        </div>

        {/* 2. Brand Suite Modules & Engine Selector */}
        <div className="space-y-4 rounded-xl border border-[#141d3d]/70 bg-[#02040a] p-4">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white font-sans text-xs">
              Active Brand Module & Engine
            </span>
            <div className="inline-flex rounded-lg border border-[#141d3d] bg-[#060b1c] p-0.5 text-[10px]">
              <button
                type="button"
                onClick={() => setPreviewRenderMode('vector')}
                className={`flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer transition ${
                  previewRenderMode === 'vector'
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Code2 className="h-3 w-3" />
                <span>Vector SVG</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewRenderMode('holographic')}
                className={`flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer transition ${
                  previewRenderMode === 'holographic'
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <ImageIcon className="h-3 w-3" />
                <span>3D Render</span>
              </button>
            </div>
          </div>

          {/* Module Cards Grid */}
          <div className="grid grid-cols-2 gap-2">
            {(['os', 'core', 'bot', 'dashboard'] as BrandLogoVariant[]).map((v) => {
              const b = BRAND_DEFINITIONS[v];
              const isSelected = selectedBrand === v;
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => setSelectedBrand(v)}
                  className={`flex items-center gap-2.5 p-2 rounded-lg border text-left transition cursor-pointer ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-950/40 text-white'
                      : 'border-[#141d3d] bg-[#060b1c]/80 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="shrink-0">
                    <BrandLogo
                      variant={v}
                      size="xs"
                      renderMode={previewRenderMode}
                      showWordmark={false}
                      showBadge={false}
                      glow={isSelected}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-bold text-xs truncate">{b.suffix}</div>
                    <div className="text-[10px] text-slate-400 truncate">{b.tagline}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Color Tokens Swatches */}
          <div className="pt-2 border-t border-[#141d3d]/50 flex items-center justify-between">
            <span className="text-[10px] text-slate-400">BRAND PALETTE:</span>
            <div className="flex gap-1.5">
              {BRAND_PALETTES.map((c) => (
                <button
                  key={c.hex}
                  type="button"
                  onClick={() => onCopyColor(c.hex, c.name)}
                  className={`group relative h-5 w-5 rounded-md ${c.bg} flex items-center justify-center transition hover:scale-110 cursor-pointer shadow-sm`}
                  title={`Copy ${c.name} (${c.hex})`}
                >
                  {copiedHex === c.hex && <Check className="h-3 w-3 text-black stroke-[3]" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
