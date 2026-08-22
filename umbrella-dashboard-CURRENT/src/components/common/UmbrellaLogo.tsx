import React from 'react';

interface UmbrellaLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showWordmark?: boolean;
  className?: string;
  subtext?: string;
}

export const UmbrellaLogo: React.FC<UmbrellaLogoProps> = ({
  size = 'md',
  showWordmark = true,
  className = '',
  subtext
}) => {
  const iconDimensions = {
    sm: 'h-6 w-6',
    md: 'h-8 w-8',
    lg: 'h-11 w-11',
    xl: 'h-14 w-14'
  };

  const textSizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl',
    xl: 'text-2xl sm:text-3xl'
  };

  const badgePadding = {
    sm: 'px-1.5 py-0.5 text-[9px]',
    md: 'px-2 py-0.5 text-[10px]',
    lg: 'px-2.5 py-0.5 text-xs',
    xl: 'px-3 py-1 text-sm'
  };

  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className}`}>
      {/* Geometric Umbrella Cyber-Shield Emblem */}
      <div className={`relative ${iconDimensions[size]} shrink-0 flex items-center justify-center`}>
        {/* Ambient Glow */}
        <div className="absolute inset-0 rounded-xl bg-cyan-500/25 blur-[6px] transition-all group-hover:bg-cyan-400/40" />

        {/* Outer Hex/Shield Container */}
        <div className="relative h-full w-full rounded-xl bg-gradient-to-b from-[#0e1726] to-[#080d1a] border border-cyan-500/40 p-1.5 flex items-center justify-center shadow-lg shadow-cyan-950/50">
          <svg
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="w-full h-full text-cyan-400"
          >
            {/* Top Spindle Pin */}
            <path
              d="M16 2.5V5.5"
              stroke="#38bdf8"
              strokeWidth="2"
              strokeLinecap="round"
            />

            {/* Geometric Umbrella Canopy Ribs */}
            {/* Left Wing */}
            <path
              d="M16 6C11 6 5.5 10 4 16C7.5 16 10 14.2 12 13.5C13.5 15.2 14.8 15.8 16 16C16 13 16 9 16 6Z"
              fill="url(#umbrella_grad_left)"
              stroke="#06b6d4"
              strokeWidth="1.2"
              strokeLinejoin="round"
            />
            {/* Right Wing */}
            <path
              d="M16 6C21 6 26.5 10 28 16C24.5 16 22 14.2 20 13.5C18.5 15.2 17.2 15.8 16 16C16 13 16 9 16 6Z"
              fill="url(#umbrella_grad_right)"
              stroke="#38bdf8"
              strokeWidth="1.2"
              strokeLinejoin="round"
            />
            {/* Center Crown Segment */}
            <path
              d="M16 6C13.8 8.8 13.2 12.5 12 13.5C14.2 15.8 15.2 16 16 16C16.8 16 17.8 15.8 20 13.5C18.8 12.5 18.2 8.8 16 6Z"
              fill="url(#umbrella_grad_center)"
              opacity="0.9"
            />

            {/* Central Shaft */}
            <path
              d="M16 15.5V23"
              stroke="#38bdf8"
              strokeWidth="2"
              strokeLinecap="round"
            />

            {/* Cybernetic J-Hook Handle with Terminal Node */}
            <path
              d="M16 23C16 25.5 14.5 27.5 12.5 27.5C10.8 27.5 9.5 26.2 9.5 24.8"
              stroke="#06b6d4"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* Glowing Accent Node */}
            <circle cx="9.5" cy="24.8" r="1.5" fill="#38bdf8" />
            <circle cx="16" cy="6" r="1.2" fill="#e0f2fe" />

            {/* Gradients */}
            <defs>
              <linearGradient id="umbrella_grad_left" x1="4" y1="6" x2="16" y2="16" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0891b2" stopOpacity="0.8" />
                <stop offset="1" stopColor="#06b6d4" stopOpacity="0.3" />
              </linearGradient>
              <linearGradient id="umbrella_grad_right" x1="28" y1="6" x2="16" y2="16" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0284c7" stopOpacity="0.8" />
                <stop offset="1" stopColor="#38bdf8" stopOpacity="0.4" />
              </linearGradient>
              <linearGradient id="umbrella_grad_center" x1="16" y1="6" x2="16" y2="16" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38bdf8" />
                <stop offset="1" stopColor="#0891b2" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>

      {/* Typography Wordmark */}
      {showWordmark && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className={`font-bold tracking-tight text-white font-mono ${textSizes[size]}`}>
              Umbrella<span className="text-cyan-400 font-extrabold ml-0.5 drop-shadow-[0_0_12px_rgba(6,182,212,0.6)]">OS</span>
            </span>
          </div>
          {subtext && (
            <span className="text-[10px] text-slate-400 font-mono tracking-wide -mt-0.5">
              {subtext}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export { UmbrellaCoreIcon, UmbrellaBotIcon, UmbrellaPluginIcon } from './UmbrellaIcons';
