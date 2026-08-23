import React, { useMemo } from 'react';

interface AtmosphericBackgroundProps {
  showDoodles?: boolean;
  doodleOpacity?: number; // 0 to 1
  showStars?: boolean;
  showHorizon?: boolean;
  variant?: 'full' | 'login' | 'subtle';
  className?: string;
}

/**
 * AtmosphericBackground:
 * Renders a midnight sky with twinkling stars, soft horizon reflections (inspired by Heaven Cloud),
 * layered with a WhatsApp-style scrambled doodle pattern of Umbrella OS, Core, Bot, and Dashboard iconography.
 */
export const AtmosphericBackground: React.FC<AtmosphericBackgroundProps> = ({
  showDoodles = true,
  doodleOpacity = 0.07,
  showStars = true,
  showHorizon = true,
  variant = 'full',
  className = ''
}) => {
  // Deterministic stars coordinates
  const stars = useMemo(() => {
    const starList = [];
    const count = variant === 'login' ? 70 : 45;
    for (let i = 0; i < count; i++) {
      // Linear pseudo-random distribution
      const x = ((i * 17.3) % 100).toFixed(1);
      const y = ((i * 31.7) % 65).toFixed(1); // Top 65% of screen
      const size = (i % 3 === 0 ? 2 : i % 2 === 0 ? 1.5 : 1).toFixed(1);
      const delay = ((i * 0.3) % 4).toFixed(1);
      const opacity = (0.3 + ((i * 7) % 60) / 100).toFixed(2);
      starList.push({ id: i, x, y, size, delay, opacity });
    }
    return starList;
  }, [variant]);

  // WhatsApp-style scrambled doodle icons matrix
  // Uses various rotations, scales, and icon types from the Umbrella suite
  const doodleIcons = useMemo(() => {
    const icons = [];
    const types = ['umbrella', 'core', 'bot', 'radar', 'shield', 'key', 'terminal', 'wifi', 'cube'];
    const cols = 8;
    const rows = 6;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = r * cols + c;
        const type = types[(idx + r * 2) % types.length];
        // Jitter positioning so it's not a rigid grid
        const x = (c * 12.5 + ((idx * 3.7) % 6) - 3).toFixed(1);
        const y = (r * 16.5 + ((idx * 5.3) % 8) - 4).toFixed(1);
        const rotation = (((idx * 43) % 140) - 70).toFixed(0); // -70deg to +70deg
        const scale = (0.75 + ((idx * 11) % 5) * 0.1).toFixed(2); // 0.75x to 1.15x
        icons.push({ id: idx, type, x, y, rotation, scale });
      }
    }
    return icons;
  }, []);

  return (
    <div
      aria-hidden="true"
      className={`fixed inset-0 pointer-events-none overflow-hidden select-none z-0 ${className}`}
    >
      {/* 1. Deep Midnight & Nocturnal Sky Gradient Base */}
      <div className="absolute inset-0 bg-[#02040a]" />

      {/* Atmospheric Radial Nebulae */}
      <div className="absolute -top-[20%] left-1/2 -translate-x-1/2 w-[1200px] h-[600px] bg-gradient-to-b from-[#0e1638]/50 via-[#070b24]/30 to-transparent blur-3xl opacity-80 rounded-full" />
      <div className="absolute top-[25%] -left-[10%] w-[600px] h-[500px] bg-[#11183c]/30 blur-3xl rounded-full" />
      <div className="absolute top-[20%] -right-[10%] w-[600px] h-[500px] bg-[#0c1945]/35 blur-3xl rounded-full" />

      {/* 2. Twinkling Stars Layer */}
      {showStars && (
        <div className="absolute inset-0">
          {stars.map((s) => (
            <div
              key={s.id}
              className="absolute rounded-full bg-slate-100 animate-pulse"
              style={{
                left: `${s.x}%`,
                top: `${s.y}%`,
                width: `${s.size}px`,
                height: `${s.size}px`,
                opacity: s.opacity,
                animationDuration: `${2 + Number(s.delay)}s`,
                animationDelay: `${s.delay}s`
              }}
            />
          ))}
        </div>
      )}

      {/* 3. WhatsApp-Style Scrambled Umbrella Suite Doodle Pattern */}
      {showDoodles && (
        <div
          className="absolute inset-0 transition-opacity duration-300"
          style={{ opacity: doodleOpacity }}
        >
          <svg className="w-full h-full text-indigo-300" xmlns="http://www.w3.org/2000/svg">
            <defs>
              {/* Umbrella OS Silhouette */}
              <g id="doodle-umbrella">
                <path d="M16 4V8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                <path
                  d="M16 9C9 9 4 15 2 21C6.5 21 10 18.5 12.5 17.5C14.5 19.8 15.5 20.5 16 20.5C16.5 20.5 17.5 19.8 19.5 17.5C22 18.5 25.5 21 30 21C28 15 23 9 16 9Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinejoin="round"
                />
                <path d="M16 20.5V27C16 29 14.5 30.5 12.5 30.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                <circle cx="12.5" cy="30.5" r="1" fill="currentColor" />
              </g>

              {/* Umbrella Core Chip */}
              <g id="doodle-core">
                <rect x="6" y="6" width="20" height="20" rx="3" stroke="currentColor" strokeWidth="1.8" fill="none" />
                <path d="M11 2V6M16 2V6M21 2V6M11 26V30M16 26V30M21 26V30" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M2 11H6M2 16H6M2 21H6M26 11H30M26 16H30M26 21H30" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M16 11C13 11 11 13 10 15.5H22C21 13 19 11 16 11Z" stroke="currentColor" strokeWidth="1.3" fill="none" />
                <path d="M16 15.5V19C16 20 15 20.5 14 20.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </g>

              {/* Umbrella Bot Visor */}
              <g id="doodle-bot">
                <path d="M16 3C13 3 11 4.5 10 6H22C21 4.5 19 3 16 3Z" stroke="currentColor" strokeWidth="1.5" fill="none" />
                <path d="M16 6V8" stroke="currentColor" strokeWidth="1.5" />
                <rect x="5" y="8" width="22" height="18" rx="5" stroke="currentColor" strokeWidth="1.8" fill="none" />
                <circle cx="11" cy="15" r="2" fill="currentColor" />
                <circle cx="21" cy="15" r="2" fill="currentColor" />
                <path d="M11 20H13L14.5 18.5L16 21L17.5 18.5L19 20H21" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </g>

              {/* Dashboard Radar Telemetry */}
              <g id="doodle-radar">
                <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="1.8" fill="none" />
                <circle cx="16" cy="16" r="7" stroke="currentColor" strokeWidth="1.2" strokeDasharray="2 2" fill="none" />
                <line x1="16" y1="4" x2="16" y2="28" stroke="currentColor" strokeWidth="1.2" />
                <line x1="4" y1="16" x2="28" y2="16" stroke="currentColor" strokeWidth="1.2" />
                <path d="M16 10C20 10 22 13 22 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </g>

              {/* Cyber Shield */}
              <g id="doodle-shield">
                <path d="M16 3L27 8V17C27 23 22 27.5 16 29C10 27.5 5 23 5 17V8L16 3Z" stroke="currentColor" strokeWidth="1.8" fill="none" />
                <path d="M16 9C13 9 10 11.5 9 14.5C12 14.5 14 13.5 16 13.5C18 13.5 20 14.5 23 14.5C22 11.5 19 9 16 9Z" stroke="currentColor" strokeWidth="1.3" fill="none" />
                <path d="M16 13.5V21C16 22 15 23 14 23" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </g>

              {/* Terminal / Code Bracket */}
              <g id="doodle-terminal">
                <rect x="4" y="6" width="24" height="20" rx="3" stroke="currentColor" strokeWidth="1.8" fill="none" />
                <path d="M8 12L12 16L8 20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="14" y1="20" x2="20" y2="20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </g>

              {/* Isometric Package Cube */}
              <g id="doodle-cube">
                <path d="M16 4L27 10V22L16 28L5 22V10L16 4Z" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinejoin="round" />
                <path d="M16 4V16M16 28V16M5 10L16 16L27 10" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              </g>

              {/* Security Key */}
              <g id="doodle-key">
                <circle cx="11" cy="16" r="6" stroke="currentColor" strokeWidth="1.8" fill="none" />
                <path d="M17 16H27V20M23 16V19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </g>

              {/* Wifi / Signal Node */}
              <g id="doodle-wifi">
                <path d="M6 10C12 4 20 4 26 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none" />
                <path d="M10 15C13.5 11 18.5 11 22 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none" />
                <circle cx="16" cy="21" r="2" fill="currentColor" />
              </g>
            </defs>

            {doodleIcons.map((d) => (
              <use
                key={d.id}
                href={`#doodle-${d.type}`}
                x={`${d.x}%`}
                y={`${d.y}%`}
                transform={`rotate(${d.rotation} ${d.x * 10} ${d.y * 10}) scale(${d.scale})`}
              />
            ))}
          </svg>
        </div>
      )}

      {/* 4. Nocturnal Horizon Line & Water Reflection (Heaven Cloud Style) */}
      {showHorizon && (
        <div className="absolute bottom-0 left-0 right-0 h-[38vh] overflow-hidden pointer-events-none">
          {/* Distant Mountain / Minecraft Island Silhouette */}
          <div className="absolute bottom-[24vh] left-0 right-0 h-12 bg-gradient-to-t from-[#050818] to-transparent opacity-90" />
          
          {/* Subtle Horizon Glow Line */}
          <div className="absolute bottom-[24vh] left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#3b82f6]/40 to-transparent" />
          
          {/* Calm Water Surface with Horizontal Reflection Ripple Gradients */}
          <div className="absolute bottom-0 left-0 right-0 h-[24vh] bg-gradient-to-b from-[#060c24]/90 via-[#030614]/95 to-[#010206] border-t border-[#141e42]/60">
            {/* Ambient Water Light Sheen */}
            <div className="absolute inset-0 bg-gradient-to-b from-[#38bdf8]/5 via-transparent to-transparent" />
            
            {/* Water Waves / Ripple Lines */}
            <div className="absolute top-2 left-[15%] right-[15%] h-[1px] bg-gradient-to-r from-transparent via-[#6366f1]/25 to-transparent blur-[0.5px]" />
            <div className="absolute top-6 left-[25%] right-[25%] h-[1px] bg-gradient-to-r from-transparent via-[#818cf8]/20 to-transparent blur-[0.5px]" />
            <div className="absolute top-12 left-[35%] right-[35%] h-[1px] bg-gradient-to-r from-transparent via-[#38bdf8]/15 to-transparent blur-[0.5px]" />
            <div className="absolute top-20 left-[20%] right-[20%] h-[1px] bg-gradient-to-r from-transparent via-[#4f46e5]/15 to-transparent blur-[0.5px]" />
          </div>
        </div>
      )}

      {/* Soft Vignette Overlay */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,#02040a_85%)] opacity-70" />
    </div>
  );
};
