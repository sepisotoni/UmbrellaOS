import React from 'react';

// Import generated high-res 3D holographic artwork assets
import uosImage from '../../assets/images/umbrella_os_logo_1787476176173.jpg';
import ucoreImage from '../../assets/images/umbrella_core_logo_1787476190653.jpg';
import ubotImage from '../../assets/images/umbrella_bot_logo_1787476205637.jpg';
import udashImage from '../../assets/images/umbrella_dashboard_logo_1787476221176.jpg';

export type BrandLogoVariant = 'os' | 'core' | 'bot' | 'dashboard';
export type LogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl';
export type LogoRenderMode = 'vector' | 'holographic';

export const BRAND_IMAGES: Record<BrandLogoVariant, string> = {
  os: uosImage,
  core: ucoreImage,
  bot: ubotImage,
  dashboard: udashImage,
};

interface BrandLogoProps {
  variant?: BrandLogoVariant;
  size?: LogoSize;
  renderMode?: LogoRenderMode;
  showWordmark?: boolean;
  showBadge?: boolean;
  className?: string;
  subtext?: string;
  glow?: boolean;
  onClick?: () => void;
}

/**
 * 1. UMBRELLA OS EMBLEM (High-End Precision Cyber Vector)
 * Cybersecurity Shield & Fleet Hypervisor
 */
export const UmbrellaOsEmblem: React.FC<{ className?: string; glow?: boolean }> = ({
  className = 'w-full h-full',
  glow = true,
}) => (
  <svg
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="uos_v2_shield_bg" x1="32" y1="4" x2="32" y2="60" gradientUnits="userSpaceOnUse">
        <stop stopColor="#0f172a" />
        <stop offset="0.5" stopColor="#090d1f" />
        <stop offset="1" stopColor="#030712" />
      </linearGradient>

      <linearGradient id="uos_v2_canopy_left" x1="10" y1="18" x2="32" y2="34" gradientUnits="userSpaceOnUse">
        <stop stopColor="#6366f1" />
        <stop offset="0.6" stopColor="#4f46e5" />
        <stop offset="1" stopColor="#312e81" />
      </linearGradient>

      <linearGradient id="uos_v2_canopy_right" x1="54" y1="18" x2="32" y2="34" gradientUnits="userSpaceOnUse">
        <stop stopColor="#818cf8" />
        <stop offset="0.6" stopColor="#6366f1" />
        <stop offset="1" stopColor="#3730a3" />
      </linearGradient>

      <linearGradient id="uos_v2_canopy_center" x1="32" y1="16" x2="32" y2="33" gradientUnits="userSpaceOnUse">
        <stop stopColor="#a5b4fc" />
        <stop offset="0.5" stopColor="#6366f1" />
        <stop offset="1" stopColor="#4338ca" />
      </linearGradient>

      <linearGradient id="uos_v2_neon_border" x1="6" y1="6" x2="58" y2="58" gradientUnits="userSpaceOnUse">
        <stop stopColor="#818cf8" />
        <stop offset="0.5" stopColor="#4f46e5" />
        <stop offset="1" stopColor="#06b6d4" />
      </linearGradient>

      <radialGradient id="uos_v2_core_glow" cx="32" cy="24" r="20" gradientUnits="userSpaceOnUse">
        <stop stopColor="#6366f1" stopOpacity="0.4" />
        <stop offset="1" stopColor="#6366f1" stopOpacity="0" />
      </radialGradient>

      <filter id="uos_glow_fx" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.5" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>

    {/* Background Glow */}
    {glow && <circle cx="32" cy="30" r="24" fill="url(#uos_v2_core_glow)" />}

    {/* Outer Hexagonal Cyber Shield */}
    <path
      d="M32 4L56 14.5V33C56 46.5 45.5 56.5 32 60C18.5 56.5 8 46.5 8 33V14.5L32 4Z"
      fill="url(#uos_v2_shield_bg)"
      stroke="url(#uos_v2_neon_border)"
      strokeWidth="1.8"
      strokeLinejoin="round"
    />

    {/* Subtle Inner Shield Grid Inset */}
    <path
      d="M32 9L50 17.5V32C50 42.5 42 50.5 32 54C22 50.5 14 42.5 14 32V17.5L32 9Z"
      stroke="#1e293b"
      strokeWidth="1"
      strokeDasharray="3 3"
      opacity="0.7"
    />

    {/* Top Spindle Energy Apex */}
    <line x1="32" y1="10" x2="32" y2="16" stroke="#c7d2fe" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="32" cy="10" r="2" fill="#38bdf8" />

    {/* Left Canopy Wing (Faceted Shield Plate) */}
    <path
      d="M32 17C22 17 14 24 12 32C18 32 22 29 25.5 27.5C28 30.5 30 31.5 32 32C32 26 32 21 32 17Z"
      fill="url(#uos_v2_canopy_left)"
      stroke="#6366f1"
      strokeWidth="1.2"
    />

    {/* Right Canopy Wing (Faceted Shield Plate) */}
    <path
      d="M32 17C42 17 50 24 52 32C46 32 42 29 38.5 27.5C36 30.5 34 31.5 32 32C32 26 32 21 32 17Z"
      fill="url(#uos_v2_canopy_right)"
      stroke="#818cf8"
      strokeWidth="1.2"
    />

    {/* Center Canopy Crown Keystroke */}
    <path
      d="M32 17C28 22 26.8 28 25.5 29.5C29 32.5 30.8 33 32 33C33.2 33 35 32.5 38.5 29.5C37.2 28 36 22 32 17Z"
      fill="url(#uos_v2_canopy_center)"
      stroke="#a5b4fc"
      strokeWidth="1.2"
    />

    {/* Canopy Highlight Edges */}
    <path d="M12 32C19 31.5 23 27 25.5 27.5" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />
    <path d="M52 32C45 31.5 41 27 38.5 27.5" stroke="#a5b4fc" strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />

    {/* Central Shaft & Microchip Conduit */}
    <line x1="32" y1="31" x2="32" y2="45" stroke="#c7d2fe" strokeWidth="3" strokeLinecap="round" />
    <line x1="32" y1="33" x2="32" y2="43" stroke="#38bdf8" strokeWidth="1.2" strokeLinecap="round" />

    {/* Cybernetic J-Hook / Security Anchor */}
    <path
      d="M32 45C32 49 29 51.5 25 51.5C21.5 51.5 19 49 19 46.5C19 45 20.2 44 21.5 44C22.8 44 23.5 45 23.5 46C23.5 47 24 48 25.5 48C27 48 28.5 46.5 28.5 44.5"
      stroke="#818cf8"
      strokeWidth="2.8"
      strokeLinecap="round"
    />

    {/* Tech Node Corner Accents */}
    <circle cx="15" cy="20" r="1.5" fill="#6366f1" />
    <circle cx="49" cy="20" r="1.5" fill="#818cf8" />
    <circle cx="32" cy="56" r="1.5" fill="#38bdf8" />
  </svg>
);

/**
 * 2. UMBRELLA CORE EMBLEM (Quantum Processor & Reactor Engine)
 * Kernel Micro-Engine, Cluster Fabric & Event Loop
 */
export const UmbrellaCoreEmblem: React.FC<{ className?: string; glow?: boolean }> = ({
  className = 'w-full h-full',
  glow = true,
}) => (
  <svg
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="ucore_v2_bg" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
        <stop stopColor="#022c22" />
        <stop offset="0.5" stopColor="#041f1a" />
        <stop offset="1" stopColor="#020617" />
      </linearGradient>

      <linearGradient id="ucore_v2_cyan_neon" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38bdf8" />
        <stop offset="0.5" stopColor="#06b6d4" />
        <stop offset="1" stopColor="#10b981" />
      </linearGradient>

      <radialGradient id="ucore_v2_reactor" cx="32" cy="32" r="16" gradientUnits="userSpaceOnUse">
        <stop stopColor="#22d3ee" />
        <stop offset="0.6" stopColor="#0891b2" />
        <stop offset="1" stopColor="#042f2e" />
      </radialGradient>
    </defs>

    {/* Outer Silicon Carrier Frame */}
    <rect
      x="8"
      y="8"
      width="48"
      height="48"
      rx="12"
      fill="url(#ucore_v2_bg)"
      stroke="url(#ucore_v2_cyan_neon)"
      strokeWidth="1.8"
    />

    {/* Bus Contact Gold Pins - Top/Bottom/Sides */}
    {[18, 26, 34, 42].map((pos) => (
      <React.Fragment key={pos}>
        <line x1={pos} y1="4" x2={pos} y2="8" stroke="#06b6d4" strokeWidth="1.5" strokeLinecap="round" />
        <line x1={pos} y1="56" x2={pos} y2="60" stroke="#06b6d4" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="4" y1={pos} x2="8" y2={pos} stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="56" y1={pos} x2="60" y2={pos} stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" />
      </React.Fragment>
    ))}

    {/* Diagonal Interconnect Circuit Traces */}
    <path d="M14 14L22 22" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M50 14L42 22" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M14 50L22 42" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M50 50L42 42" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round" />

    {/* Upper Umbrella Canopy Arc Intertwined in Processor */}
    <path
      d="M16 26C20 18 44 18 48 26C42 27.5 38 24.5 32 25C26 24.5 22 27.5 16 26Z"
      fill="#0e7490"
      stroke="#22d3ee"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />

    {/* Central Hex Quantum Core / Reactor */}
    <polygon
      points="32,22 41,27 41,37 32,42 23,37 23,27"
      fill="url(#ucore_v2_reactor)"
      stroke="#67e8f9"
      strokeWidth="1.8"
      strokeLinejoin="round"
    />

    {/* Inner Reactor Node & Pulsing Core Light */}
    <circle cx="32" cy="32" r="4.5" fill="#ecfeff" />
    <circle cx="32" cy="32" r="2" fill="#06b6d4" />

    {/* Shaft / Data Bus Path */}
    <line x1="32" y1="42" x2="32" y2="49" stroke="#67e8f9" strokeWidth="2.5" strokeLinecap="round" />
    <path
      d="M32 49C32 52 30 53.5 27 53.5C24.5 53.5 23 52 23 50.5"
      stroke="#22d3ee"
      strokeWidth="2.2"
      strokeLinecap="round"
    />

    {/* Micro-nodes */}
    <circle cx="23" cy="27" r="1.5" fill="#a5f3fc" />
    <circle cx="41" cy="27" r="1.5" fill="#a5f3fc" />
  </svg>
);

/**
 * 3. UMBRELLA BOT EMBLEM (Cyber Sentinel & Autonomous AI Companion)
 * Discord Sentinel, Event Automator & Moderation Android
 */
export const UmbrellaBotEmblem: React.FC<{ className?: string; glow?: boolean }> = ({
  className = 'w-full h-full',
  glow = true,
}) => (
  <svg
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="ubot_v2_helm_grad" x1="12" y1="12" x2="52" y2="54" gradientUnits="userSpaceOnUse">
        <stop stopColor="#311042" />
        <stop offset="0.5" stopColor="#1e0c33" />
        <stop offset="1" stopColor="#070212" />
      </linearGradient>

      <linearGradient id="ubot_v2_canopy_crest" x1="16" y1="10" x2="48" y2="24" gradientUnits="userSpaceOnUse">
        <stop stopColor="#c084fc" />
        <stop offset="0.5" stopColor="#a855f7" />
        <stop offset="1" stopColor="#7e22ce" />
      </linearGradient>

      <linearGradient id="ubot_v2_visor_glass" x1="16" y1="30" x2="48" y2="44" gradientUnits="userSpaceOnUse">
        <stop stopColor="#06b6d4" />
        <stop offset="0.5" stopColor="#3b82f6" />
        <stop offset="1" stopColor="#6366f1" />
      </linearGradient>
    </defs>

    {/* Outer Bot Head Armor */}
    <rect
      x="12"
      y="18"
      width="40"
      height="38"
      rx="12"
      fill="url(#ubot_v2_helm_grad)"
      stroke="#a855f7"
      strokeWidth="1.8"
    />

    {/* Side Audio Equalizer Antennae Ears */}
    {/* Left Ear */}
    <path
      d="M6 28C6 24 9 22 12 22V42C9 42 6 40 6 36V28Z"
      fill="#2e1065"
      stroke="#c084fc"
      strokeWidth="1.4"
    />
    <line x1="8" y1="28" x2="8" y2="36" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" />

    {/* Right Ear */}
    <path
      d="M58 28C58 24 55 22 52 22V42C55 42 58 40 58 36V28Z"
      fill="#2e1065"
      stroke="#c084fc"
      strokeWidth="1.4"
    />
    <line x1="56" y1="28" x2="56" y2="36" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" />

    {/* Umbrella Canopy Forehead Crest */}
    <path
      d="M16 18C20 10 44 10 48 18C42 20 38 17 32 17.5C26 17 22 20 16 18Z"
      fill="url(#ubot_v2_canopy_crest)"
      stroke="#e9d5ff"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />

    {/* Apex Top Beacon Sensor */}
    <circle cx="32" cy="7" r="2.5" fill="#38bdf8" />
    <line x1="32" y1="9.5" x2="32" y2="13" stroke="#c084fc" strokeWidth="2" strokeLinecap="round" />

    {/* Wide Holographic Optic Visor Screen */}
    <rect
      x="17"
      y="28"
      width="30"
      height="14"
      rx="6"
      fill="#030712"
      stroke="url(#ubot_v2_visor_glass)"
      strokeWidth="1.5"
    />

    {/* Cybernetic Expressive Robot Eyes (Glowing Cyan Neon) */}
    <circle cx="25" cy="35" r="3.5" fill="#38bdf8" />
    <circle cx="26" cy="34" r="1.2" fill="#ffffff" />

    <circle cx="39" cy="35" r="3.5" fill="#38bdf8" />
    <circle cx="40" cy="34" r="1.2" fill="#ffffff" />

    {/* Tactical Visor Grid Line */}
    <line x1="19" y1="32" x2="45" y2="32" stroke="#38bdf8" strokeWidth="0.6" strokeDasharray="2 2" opacity="0.5" />

    {/* Lower Mouth Speaker Grill / J-Hook Shaft Accent */}
    <line x1="28" y1="47" x2="36" y2="47" stroke="#a855f7" strokeWidth="1.8" strokeLinecap="round" />
    <line x1="30" y1="50" x2="34" y2="50" stroke="#c084fc" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

/**
 * 4. UMBRELLA DASHBOARD EMBLEM (Radar Telemetry & Mission Control)
 * Live Telemetry Hub, Minecraft Monitor & Analytics Matrix
 */
export const UmbrellaDashboardEmblem: React.FC<{ className?: string; glow?: boolean }> = ({
  className = 'w-full h-full',
  glow = true,
}) => (
  <svg
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="udash_v2_bg" x1="10" y1="10" x2="54" y2="54" gradientUnits="userSpaceOnUse">
        <stop stopColor="#082f49" />
        <stop offset="0.5" stopColor="#031f38" />
        <stop offset="1" stopColor="#020617" />
      </linearGradient>

      <linearGradient id="udash_v2_radar_ring" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38bdf8" />
        <stop offset="0.5" stopColor="#0ea5e9" />
        <stop offset="1" stopColor="#6366f1" />
      </linearGradient>

      <linearGradient id="udash_v2_canopy_radar" x1="16" y1="16" x2="48" y2="36" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38bdf8" />
        <stop offset="0.5" stopColor="#0284c7" />
        <stop offset="1" stopColor="#1e3a8a" />
      </linearGradient>
    </defs>

    {/* Outer Gauge Frame */}
    <circle
      cx="32"
      cy="32"
      r="24"
      fill="url(#udash_v2_bg)"
      stroke="url(#udash_v2_radar_ring)"
      strokeWidth="1.8"
    />

    {/* Outer Orbit Tick Marks */}
    <circle
      cx="32"
      cy="32"
      r="19"
      stroke="#0ea5e9"
      strokeWidth="0.8"
      strokeDasharray="3 4"
      opacity="0.6"
    />

    {/* Telemetry Equalizer Bars (Live Metrics at bottom of dial) */}
    <rect x="22" y="44" width="3" height="5" rx="1.5" fill="#10b981" />
    <rect x="27" y="41" width="3" height="8" rx="1.5" fill="#38bdf8" />
    <rect x="32" y="39" width="3" height="10" rx="1.5" fill="#6366f1" />
    <rect x="37" y="42" width="3" height="7" rx="1.5" fill="#a855f7" />
    <rect x="42" y="45" width="3" height="4" rx="1.5" fill="#38bdf8" />

    {/* Upper Radar Canopy Arch */}
    <path
      d="M18 28C22 17 42 17 46 28C41 29.5 37 26.5 32 27C27 26.5 23 29.5 18 28Z"
      fill="url(#udash_v2_canopy_radar)"
      stroke="#7dd3fc"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />

    {/* Radar Sweep Needle Compass */}
    <line x1="32" y1="12" x2="32" y2="32" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />
    <polygon points="32,8 35,14 29,14" fill="#38bdf8" />

    {/* Central Target Pivot Node */}
    <circle cx="32" cy="32" r="4" fill="#0284c7" stroke="#e0f2fe" strokeWidth="1.5" />
    <circle cx="32" cy="32" r="1.5" fill="#ffffff" />

    {/* Target Quadrant Markers */}
    <line x1="14" y1="32" x2="20" y2="32" stroke="#0ea5e9" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="44" y1="32" x2="50" y2="32" stroke="#0ea5e9" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

/**
 * Brand Definitions Dictionary with full metadata, theme colors, and icons
 */
export const BRAND_DEFINITIONS: Record<
  BrandLogoVariant,
  {
    name: string;
    suffix: string;
    tagline: string;
    description: string;
    primaryColor: string;
    accentColor: string;
    glowClass: string;
    borderClass: string;
    badgeBg: string;
    Component: React.FC<{ className?: string; glow?: boolean }>;
    imageAsset: string;
    svgCode: string;
  }
> = {
  os: {
    name: 'Umbrella',
    suffix: 'OS',
    tagline: 'Cybersecurity Shield & Minecraft Fleet Hypervisor',
    description:
      'The foundational core hypervisor, container orchestrator, network security gateway, and central management layer.',
    primaryColor: '#6366f1',
    accentColor: '#38bdf8',
    glowClass: 'shadow-[0_0_25px_rgba(99,102,241,0.45)]',
    borderClass: 'border-indigo-500/50',
    badgeBg: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
    Component: UmbrellaOsEmblem,
    imageAsset: uosImage,
    svgCode: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Umbrella OS Official Cyber Shield Emblem -->
  <path d="M32 4L56 14.5V33C56 46.5 45.5 56.5 32 60C18.5 56.5 8 46.5 8 33V14.5L32 4Z" fill="#090d1f" stroke="#6366f1" stroke-width="2"/>
  <line x1="32" y1="10" x2="32" y2="16" stroke="#c7d2fe" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="32" cy="10" r="2" fill="#38bdf8"/>
  <path d="M32 17C22 17 14 24 12 32C18 32 22 29 25.5 27.5C28 30.5 30 31.5 32 32C32 26 32 21 32 17Z" fill="#4f46e5" stroke="#6366f1" stroke-width="1.2"/>
  <path d="M32 17C42 17 50 24 52 32C46 32 42 29 38.5 27.5C36 30.5 34 31.5 32 32C32 26 32 21 32 17Z" fill="#6366f1" stroke="#818cf8" stroke-width="1.2"/>
  <line x1="32" y1="31" x2="32" y2="45" stroke="#c7d2fe" stroke-width="3" stroke-linecap="round"/>
  <path d="M32 45C32 49 29 51.5 25 51.5C21.5 51.5 19 49 19 46.5" stroke="#818cf8" stroke-width="2.8" stroke-linecap="round"/>
</svg>`,
  },
  core: {
    name: 'Umbrella',
    suffix: 'Core',
    tagline: 'High-Throughput Quantum Server Engine & Event Fabric',
    description:
      'Backend daemon micro-service, RPC bridge, Spigot plugin bus, WebSocket pub/sub telemetry broker, and distributed state engine.',
    primaryColor: '#06b6d4',
    accentColor: '#10b981',
    glowClass: 'shadow-[0_0_25px_rgba(6,182,212,0.45)]',
    borderClass: 'border-cyan-500/50',
    badgeBg: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    Component: UmbrellaCoreEmblem,
    imageAsset: ucoreImage,
    svgCode: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Umbrella Core Quantum Processor Emblem -->
  <rect x="8" y="8" width="48" height="48" rx="12" fill="#041f1a" stroke="#06b6d4" stroke-width="2"/>
  <path d="M16 26C20 18 44 18 48 26C42 27.5 38 24.5 32 25C26 24.5 22 27.5 16 26Z" fill="#0e7490" stroke="#22d3ee" stroke-width="1.5"/>
  <polygon points="32,22 41,27 41,37 32,42 23,37 23,27" fill="#0891b2" stroke="#67e8f9" stroke-width="2"/>
  <circle cx="32" cy="32" r="3" fill="#ffffff"/>
  <line x1="32" y1="42" x2="32" y2="49" stroke="#67e8f9" stroke-width="2.5" stroke-linecap="round"/>
</svg>`,
  },
  bot: {
    name: 'Umbrella',
    suffix: 'Bot',
    tagline: 'Autonomous Discord Sentinel & AI Moderation Companion',
    description:
      'Discord bot integration, AI prompt commands, role auto-synchronization, live player verification, and voice/chat alerts.',
    primaryColor: '#a855f7',
    accentColor: '#38bdf8',
    glowClass: 'shadow-[0_0_25px_rgba(168,85,247,0.45)]',
    borderClass: 'border-purple-500/50',
    badgeBg: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    Component: UmbrellaBotEmblem,
    imageAsset: ubotImage,
    svgCode: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Umbrella Bot Autonomous Sentinel Emblem -->
  <rect x="12" y="18" width="40" height="38" rx="12" fill="#1e0c33" stroke="#a855f7" stroke-width="2"/>
  <path d="M16 18C20 10 44 10 48 18C42 20 38 17 32 17.5C26 17 22 20 16 18Z" fill="#7e22ce" stroke="#c084fc" stroke-width="1.5"/>
  <rect x="17" y="28" width="30" height="14" rx="6" fill="#030712" stroke="#38bdf8" stroke-width="1.5"/>
  <circle cx="25" cy="35" r="3" fill="#38bdf8"/>
  <circle cx="39" cy="35" r="3" fill="#38bdf8"/>
</svg>`,
  },
  dashboard: {
    name: 'Umbrella',
    suffix: 'Dashboard',
    tagline: 'Live Mission Control, Node Telemetry & Analytics Hub',
    description:
      'Responsive web UI, node monitoring gauges, player manager, live console terminal, player logs, and audit inspectors.',
    primaryColor: '#38bdf8',
    accentColor: '#6366f1',
    glowClass: 'shadow-[0_0_25px_rgba(56,189,248,0.45)]',
    borderClass: 'border-sky-500/50',
    badgeBg: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
    Component: UmbrellaDashboardEmblem,
    imageAsset: udashImage,
    svgCode: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Umbrella Dashboard Mission Control Emblem -->
  <circle cx="32" cy="32" r="24" fill="#031f38" stroke="#38bdf8" stroke-width="2"/>
  <path d="M18 28C22 17 42 17 46 28C41 29.5 37 26.5 32 27C27 26.5 23 29.5 18 28Z" fill="#0284c7" stroke="#7dd3fc" stroke-width="1.5"/>
  <line x1="32" y1="12" x2="32" y2="32" stroke="#38bdf8" stroke-width="2" stroke-linecap="round"/>
  <circle cx="32" cy="32" r="3.5" fill="#ffffff"/>
</svg>`,
  },
};

const SIZE_MAP: Record<LogoSize, { box: string; icon: string; text: string; sub: string }> = {
  xs: { box: 'h-6 w-6', icon: 'h-4 w-4', text: 'text-xs', sub: 'text-[9px]' },
  sm: { box: 'h-8 w-8', icon: 'h-5 w-5', text: 'text-sm', sub: 'text-[10px]' },
  md: { box: 'h-10 w-10', icon: 'h-6 w-6', text: 'text-base', sub: 'text-xs' },
  lg: { box: 'h-14 w-14', icon: 'h-8 w-8', text: 'text-xl', sub: 'text-xs' },
  xl: { box: 'h-20 w-20', icon: 'h-12 w-12', text: 'text-2xl', sub: 'text-sm' },
  '2xl': { box: 'h-28 w-28', icon: 'h-18 w-18', text: 'text-3xl', sub: 'text-base' },
  '3xl': { box: 'h-36 w-36', icon: 'h-24 w-24', text: 'text-4xl', sub: 'text-lg' },
};

/**
 * Universal Brand Logo Component
 * Renders high-definition SVG vector or 3D Holographic render with wordmark, glow, and badge
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  variant = 'os',
  size = 'md',
  renderMode = 'vector',
  showWordmark = false,
  showBadge = false,
  className = '',
  subtext,
  glow = true,
  onClick,
}) => {
  const brand = BRAND_DEFINITIONS[variant] || BRAND_DEFINITIONS.os;
  const Emblem = brand.Component;
  const sz = SIZE_MAP[size] || SIZE_MAP.md;

  return (
    <div
      onClick={onClick}
      className={`inline-flex items-center gap-3 ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {/* Emblem Frame */}
      <div
        className={`relative flex items-center justify-center shrink-0 rounded-2xl transition-all duration-300 ${
          sz.box
        } ${glow ? brand.glowClass : ''} overflow-hidden`}
      >
        {renderMode === 'holographic' ? (
          <img
            src={brand.imageAsset}
            alt={`${brand.name} ${brand.suffix}`}
            referrerPolicy="no-referrer"
            className="w-full h-full object-cover rounded-2xl transform transition-transform hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center p-1">
            <Emblem className="w-full h-full" glow={glow} />
          </div>
        )}
      </div>

      {/* Optional Wordmark */}
      {showWordmark && (
        <div className="flex flex-col leading-tight">
          <div className="flex items-center gap-1 font-bold tracking-tight text-white font-sans">
            <span className={sz.text}>{brand.name}</span>
            <span
              className={`${sz.text} font-mono font-black text-transparent bg-clip-text`}
              style={{
                backgroundImage: `linear-gradient(135deg, ${brand.primaryColor}, ${brand.accentColor})`,
              }}
            >
              {brand.suffix}
            </span>
          </div>
          {subtext !== undefined ? (
            <span className={`text-slate-400 font-mono ${sz.sub}`}>{subtext}</span>
          ) : (
            <span className={`text-slate-400 font-mono ${sz.sub}`}>{brand.tagline}</span>
          )}
        </div>
      )}
    </div>
  );
};
