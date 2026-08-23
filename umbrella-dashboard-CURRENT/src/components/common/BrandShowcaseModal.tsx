import React, { useState } from 'react';
import {
  X,
  Copy,
  Check,
  Download,
  Sparkles,
  Shield,
  Cpu,
  Bot,
  LayoutDashboard,
  Sliders,
  Eye,
  Layers,
  Code2,
  Image as ImageIcon,
  Palette,
  ExternalLink,
} from 'lucide-react';
import {
  BrandLogo,
  BrandLogoVariant,
  BRAND_DEFINITIONS,
  LogoRenderMode,
} from './BrandLogos';

interface BrandShowcaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectBrand?: (variant: BrandLogoVariant) => void;
  selectedBrand?: BrandLogoVariant;
  doodleOpacity: number;
  onDoodleOpacityChange: (opacity: number) => void;
  showDoodles: boolean;
  onToggleDoodles: (enabled: boolean) => void;
}

export const BrandShowcaseModal: React.FC<BrandShowcaseModalProps> = ({
  isOpen,
  onClose,
  doodleOpacity,
  onDoodleOpacityChange,
  showDoodles,
  onToggleDoodles,
}) => {
  const [activeVariant, setActiveVariant] = useState<BrandLogoVariant>('os');
  const [renderMode, setRenderMode] = useState<LogoRenderMode>('holographic');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'preview' | 'wallpaper' | 'specs'>('preview');

  if (!isOpen) return null;

  const currentBrand = BRAND_DEFINITIONS[activeVariant];
  const Emblem = currentBrand.Component;

  const handleCopySvg = () => {
    navigator.clipboard.writeText(currentBrand.svgCode);
    setCopiedKey('svg');
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleCopyHex = (hex: string) => {
    navigator.clipboard.writeText(hex);
    setCopiedKey(hex);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownloadArtwork = () => {
    const link = document.createElement('a');
    link.href = currentBrand.imageAsset;
    link.download = `umbrella_${activeVariant}_emblem_3d.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const variants: {
    id: BrandLogoVariant;
    label: string;
    icon: React.FC<{ className?: string }>;
  }[] = [
    { id: 'os', label: 'Umbrella OS', icon: Shield },
    { id: 'core', label: 'Umbrella Core', icon: Cpu },
    { id: 'bot', label: 'Umbrella Bot', icon: Bot },
    { id: 'dashboard', label: 'Umbrella Dashboard', icon: LayoutDashboard },
  ];

  return (
    <div
      id="brand-showcase-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/85 backdrop-blur-md font-sans select-none"
    >
      <div className="w-full max-w-4xl rounded-2xl border border-[#141d3d] bg-[#060b1c]/95 shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Top Navigation Bar */}
        <div className="flex items-center justify-between border-b border-[#141d3d] bg-[#02040a] px-5 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-indigo-500/40 bg-indigo-950/60 text-indigo-400">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm md:text-base font-bold text-white tracking-tight flex items-center gap-2">
                <span>Umbrella Brand & Visual Asset Suite</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-700/40">
                  Next-Gen
                </span>
              </h2>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Ultra-high-definition 3D holographic renders and precision vector SVG marks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Tabs */}
            <div className="flex rounded-lg border border-[#141d3d] bg-[#02040a] p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setActiveTab('preview')}
                className={`px-3 py-1 rounded-md font-medium transition cursor-pointer ${
                  activeTab === 'preview'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Logos
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('specs')}
                className={`px-3 py-1 rounded-md font-medium transition cursor-pointer ${
                  activeTab === 'specs'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Palette
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('wallpaper')}
                className={`px-3 py-1 rounded-md font-medium transition cursor-pointer ${
                  activeTab === 'wallpaper'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Wallpaper
              </button>
            </div>

            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-[#0a122e] hover:text-white transition cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 md:p-6 space-y-6">
          {/* 1. Module Selector Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {variants.map((v) => {
              const isActive = activeVariant === v.id;
              const b = BRAND_DEFINITIONS[v.id];
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setActiveVariant(v.id)}
                  className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition text-left cursor-pointer ${
                    isActive
                      ? 'bg-indigo-950/70 border-indigo-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.25)]'
                      : 'bg-[#02040a] border-[#141d3d] text-slate-400 hover:text-slate-200 hover:bg-[#080e28]'
                  }`}
                >
                  <div className="h-9 w-9 rounded-lg bg-[#0c1433] border border-[#1a2552] overflow-hidden shrink-0 flex items-center justify-center p-0.5">
                    {renderMode === 'holographic' ? (
                      <img
                        src={b.imageAsset}
                        alt={b.name}
                        referrerPolicy="no-referrer"
                        className="h-full w-full object-cover rounded-md"
                      />
                    ) : (
                      <b.Component className="h-6 w-6" glow={isActive} />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold truncate text-white">
                      {b.name} <span className="font-mono font-black">{b.suffix}</span>
                    </div>
                    <div className="text-[10px] text-slate-500 truncate font-mono">
                      {v.id === 'os'
                        ? 'Hypervisor'
                        : v.id === 'core'
                        ? 'Reactor'
                        : v.id === 'bot'
                        ? 'Sentinel'
                        : 'Mission Control'}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {activeTab === 'preview' && (
            <div className="space-y-6">
              {/* Main Showcase Stage */}
              <div className="relative rounded-2xl border border-[#141d3d] bg-gradient-to-b from-[#0a1128] to-[#02040a] p-6 md:p-8 flex flex-col md:flex-row items-center gap-8 overflow-hidden shadow-inner">
                {/* Background Ambient Glow */}
                <div
                  className="absolute -top-16 -left-16 w-64 h-64 rounded-full blur-3xl opacity-20 pointer-events-none"
                  style={{ backgroundColor: currentBrand.primaryColor }}
                />

                {/* Main Hero Emblem Display */}
                <div className="relative flex flex-col items-center shrink-0">
                  <div
                    className={`relative h-44 w-44 md:h-52 md:w-52 rounded-3xl border border-[#1e293b] bg-[#02040a]/90 p-3 shadow-2xl flex items-center justify-center overflow-hidden transition-all duration-300 ${currentBrand.glowClass}`}
                  >
                    {renderMode === 'holographic' ? (
                      <img
                        src={currentBrand.imageAsset}
                        alt={`${currentBrand.name} ${currentBrand.suffix}`}
                        referrerPolicy="no-referrer"
                        className="w-full h-full object-cover rounded-2xl shadow-2xl transition-transform hover:scale-105"
                      />
                    ) : (
                      <div className="w-full h-full p-2">
                        <Emblem className="w-full h-full" glow={true} />
                      </div>
                    )}
                  </div>

                  {/* Render Mode Switcher Bar */}
                  <div className="mt-3 flex rounded-xl border border-[#141d3d] bg-[#02040a] p-1 text-[11px] font-mono">
                    <button
                      type="button"
                      onClick={() => setRenderMode('holographic')}
                      className={`flex items-center gap-1 px-3 py-1 rounded-lg transition cursor-pointer ${
                        renderMode === 'holographic'
                          ? 'bg-indigo-600 text-white font-bold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <ImageIcon className="h-3 w-3" />
                      <span>3D Holographic</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setRenderMode('vector')}
                      className={`flex items-center gap-1 px-3 py-1 rounded-lg transition cursor-pointer ${
                        renderMode === 'vector'
                          ? 'bg-indigo-600 text-white font-bold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Code2 className="h-3 w-3" />
                      <span>Vector SVG</span>
                    </button>
                  </div>
                </div>

                {/* Details & Actions Column */}
                <div className="flex-1 space-y-4 text-center md:text-left">
                  <div>
                    <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs font-mono mb-2"
                      style={{
                        borderColor: `${currentBrand.primaryColor}60`,
                        backgroundColor: `${currentBrand.primaryColor}15`,
                        color: currentBrand.accentColor,
                      }}
                    >
                      <span className="h-1.5 w-1.5 rounded-full animate-ping" style={{ backgroundColor: currentBrand.accentColor }} />
                      <span>OFFICIAL BRAND MARK</span>
                    </div>

                    <h3 className="text-2xl md:text-3xl font-black tracking-tight text-white font-sans flex items-center justify-center md:justify-start gap-2">
                      <span>{currentBrand.name}</span>
                      <span
                        className="font-mono text-transparent bg-clip-text"
                        style={{
                          backgroundImage: `linear-gradient(135deg, ${currentBrand.primaryColor}, ${currentBrand.accentColor})`,
                        }}
                      >
                        {currentBrand.suffix}
                      </span>
                    </h3>

                    <p className="text-sm text-indigo-200/90 font-mono mt-1">
                      {currentBrand.tagline}
                    </p>

                    <p className="text-xs text-slate-400 leading-relaxed mt-2 max-w-lg">
                      {currentBrand.description}
                    </p>
                  </div>

                  {/* Quick Action Buttons */}
                  <div className="pt-2 flex flex-wrap items-center justify-center md:justify-start gap-2.5">
                    <button
                      type="button"
                      onClick={handleCopySvg}
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-indigo-500/40 bg-indigo-950/60 hover:bg-indigo-900/80 text-xs font-semibold text-indigo-200 transition cursor-pointer"
                    >
                      {copiedKey === 'svg' ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-300">SVG Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5 text-indigo-400" />
                          <span>Copy Clean SVG Code</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={handleDownloadArtwork}
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-[#141d3d] bg-[#02040a] hover:bg-[#0a122e] text-xs font-semibold text-slate-200 transition cursor-pointer"
                    >
                      <Download className="h-3.5 w-3.5 text-slate-400" />
                      <span>Download High-Res 3D Emblem</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Multi-Size Scaling Inspector */}
              <div className="rounded-xl border border-[#141d3d] bg-[#02040a] p-4">
                <div className="text-xs font-bold text-slate-300 mb-3 flex items-center justify-between">
                  <span>RESPONSIVE SCALING PREVIEW</span>
                  <span className="text-[10px] font-mono text-slate-500">24px • 40px • 56px • 80px</span>
                </div>
                <div className="flex flex-wrap items-end gap-6 p-4 rounded-lg bg-[#060b1c]/80 border border-[#101838]">
                  <div className="flex flex-col items-center gap-1.5">
                    <BrandLogo variant={activeVariant} size="xs" renderMode={renderMode} glow={false} />
                    <span className="text-[9px] font-mono text-slate-500">xs (24px)</span>
                  </div>
                  <div className="flex flex-col items-center gap-1.5">
                    <BrandLogo variant={activeVariant} size="sm" renderMode={renderMode} glow={false} />
                    <span className="text-[9px] font-mono text-slate-500">sm (32px)</span>
                  </div>
                  <div className="flex flex-col items-center gap-1.5">
                    <BrandLogo variant={activeVariant} size="md" renderMode={renderMode} glow={true} />
                    <span className="text-[9px] font-mono text-slate-500">md (40px)</span>
                  </div>
                  <div className="flex flex-col items-center gap-1.5">
                    <BrandLogo variant={activeVariant} size="lg" renderMode={renderMode} glow={true} />
                    <span className="text-[9px] font-mono text-slate-500">lg (56px)</span>
                  </div>
                  <div className="flex flex-col items-center gap-1.5">
                    <BrandLogo variant={activeVariant} size="xl" renderMode={renderMode} glow={true} />
                    <span className="text-[9px] font-mono text-slate-500">xl (80px)</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'specs' && (
            <div className="space-y-4">
              <div className="rounded-xl border border-[#141d3d] bg-[#02040a] p-5 space-y-4">
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
                  Color System & Palette Tokens
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  {variants.map((v) => {
                    const b = BRAND_DEFINITIONS[v.id];
                    return (
                      <div key={v.id} className="p-3.5 rounded-xl border border-[#141d3d] bg-[#060b1c] space-y-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="h-3 w-3 rounded-full"
                            style={{ backgroundColor: b.primaryColor }}
                          />
                          <span className="text-xs font-bold text-white">
                            {b.name} {b.suffix}
                          </span>
                        </div>

                        <div className="space-y-1.5 font-mono text-xs">
                          <button
                            type="button"
                            onClick={() => handleCopyHex(b.primaryColor)}
                            className="w-full flex items-center justify-between p-1.5 rounded bg-[#02040a] hover:bg-[#0d1738] text-slate-300 cursor-pointer"
                          >
                            <span className="text-[10px] text-slate-500">Primary:</span>
                            <span className="font-bold">{b.primaryColor}</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => handleCopyHex(b.accentColor)}
                            className="w-full flex items-center justify-between p-1.5 rounded bg-[#02040a] hover:bg-[#0d1738] text-slate-300 cursor-pointer"
                          >
                            <span className="text-[10px] text-slate-500">Accent:</span>
                            <span className="font-bold">{b.accentColor}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'wallpaper' && (
            <div className="rounded-xl border border-[#141d3d] bg-[#02040a] p-5 space-y-6">
              <div>
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
                  Heaven Cloud Night Sky & Scrambled Pattern
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Adjust the atmospheric background wallpaper inspired by Heaven Cloud night sky and WhatsApp-style scattered doodles.
                </p>
              </div>

              <div className="space-y-4 max-w-lg">
                {/* Toggle Doodles */}
                <div className="flex items-center justify-between p-3 rounded-xl border border-[#141d3d] bg-[#060b1c]">
                  <div>
                    <div className="text-xs font-semibold text-white">Scrambled Logo Doodles</div>
                    <div className="text-[11px] text-slate-400">Scattered umbrella suite emblems at varied angles</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onToggleDoodles(!showDoodles)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition cursor-pointer ${
                      showDoodles ? 'bg-indigo-600' : 'bg-slate-800'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                        showDoodles ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                {/* Opacity Slider */}
                <div className="p-3 rounded-xl border border-[#141d3d] bg-[#060b1c] space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-white font-medium">Doodle Pattern Opacity</span>
                    <span className="font-mono text-indigo-400">{Math.round(doodleOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.01"
                    max="0.25"
                    step="0.01"
                    value={doodleOpacity}
                    onChange={(e) => onDoodleOpacityChange(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[#141d3d] bg-[#02040a] px-6 py-3 flex items-center justify-between text-xs text-slate-400 font-mono">
          <div>UmbrellaOS Design System • Vector & 3D Render Engine</div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
