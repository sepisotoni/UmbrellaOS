import React, { useId } from 'react';

interface UmbrellaSignalMarkProps {
  className?: string;
}

export const UmbrellaSignalMark: React.FC<UmbrellaSignalMarkProps> = ({
  className = '',
}) => {
  const gradientPrefix = useId().replace(/:/g, '');
  const shieldGradient = `${gradientPrefix}-shield`;
  const edgeGradient = `${gradientPrefix}-edge`;
  const coreGradient = `${gradientPrefix}-core`;

  return (
  <svg
    viewBox="0 0 120 120"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    aria-label="UmbrellaOS orbital signal mark"
    className={className}
  >
    <defs>
      <linearGradient id={shieldGradient} x1="25" y1="18" x2="95" y2="100" gradientUnits="userSpaceOnUse">
        <stop stopColor="#182452" />
        <stop offset="1" stopColor="#070B19" />
      </linearGradient>
      <linearGradient id={edgeGradient} x1="22" y1="20" x2="96" y2="96" gradientUnits="userSpaceOnUse">
        <stop stopColor="#818CF8" />
        <stop offset=".55" stopColor="#38BDF8" />
        <stop offset="1" stopColor="#6366F1" />
      </linearGradient>
      <radialGradient id={coreGradient} cx="0" cy="0" r="1" gradientTransform="translate(60 50) rotate(90) scale(34)" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" stopOpacity=".24" />
        <stop offset="1" stopColor="#38BDF8" stopOpacity="0" />
      </radialGradient>
    </defs>

    <circle cx="60" cy="60" r="48" fill={`url(#${coreGradient})`} />

    <g className="origin-center motion-safe:animate-spin motion-reduce:animate-none" style={{ animationDuration: '28s' }}>
      <circle cx="60" cy="60" r="52" stroke="#334155" strokeOpacity=".7" strokeDasharray="1 7" strokeLinecap="round" />
      <path d="M60 8a52 52 0 0 1 36.77 15.23" stroke={`url(#${edgeGradient})`} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="96.5" cy="23.5" r="3" fill="#38BDF8" />
      <circle cx="23.5" cy="96.5" r="2" fill="#818CF8" fillOpacity=".8" />
    </g>

    <path
      d="M60 19 91 33v24c0 20.2-12.6 34.8-31 44-18.4-9.2-31-23.8-31-44V33l31-14Z"
      fill={`url(#${shieldGradient})`}
      stroke={`url(#${edgeGradient})`}
      strokeWidth="1.8"
      strokeLinejoin="round"
    />
    <path d="M36 51c4.2-12.7 14.1-19 24-19s19.8 6.3 24 19c-9.7.1-15.5-4.1-24-3.1-8.5-1-14.3 3.2-24 3.1Z" fill="#4F46E5" fillOpacity=".9" />
    <path d="M36 51c8.8.1 14.8-3.9 24-3.1 9.2-.8 15.2 3.2 24 3.1" stroke="#A5B4FC" strokeWidth="1.4" strokeLinecap="round" />
    <path d="M60 47v25c0 7.7-5.3 12.5-12.2 12.5-5.7 0-9.8-3.7-9.8-8.3 0-2.8 1.8-4.9 4.2-4.9 2 0 3.5 1.4 3.5 3.2" stroke="#C7D2FE" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M60 53v19" stroke="#38BDF8" strokeWidth="1.2" strokeLinecap="round" />
    <circle cx="60" cy="47" r="3.3" fill="#E0F2FE" className="motion-safe:animate-pulse motion-reduce:animate-none" />
    <path d="M49 92h22" stroke="#38BDF8" strokeOpacity=".65" strokeWidth="1.2" strokeLinecap="round" />
  </svg>
  );
};
