import React from 'react';

interface IconProps {
  className?: string;
  size?: number | string;
}

/**
 * UmbrellaCoreIcon
 * Represents the Umbrella-Core JVM Bridge & Multi-Node Cluster Kernel
 */
export const UmbrellaCoreIcon: React.FC<IconProps> = ({ className = 'h-4 w-4', size }) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={size ? { width: size, height: size } : undefined}
    >
      {/* Outer Processor Die / Chip Frame */}
      <rect
        x="4"
        y="4"
        width="16"
        height="16"
        rx="3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      
      {/* North / South Bus Traces */}
      <path d="M8 2V4M12 2V4M16 2V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M8 20V22M12 20V22M16 20V22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      
      {/* West / East Bus Traces */}
      <path d="M2 8H4M2 12H4M2 16H4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 8H22M20 12H22M20 16H22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      
      {/* Central Micro-Umbrella Silicon Core */}
      <path
        d="M12 7.5C9.5 7.5 7.5 9.5 7.5 12H16.5C16.5 9.5 14.5 7.5 12 7.5Z"
        fill="currentColor"
        fillOpacity="0.25"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <path d="M12 12V15C12 15.8 11.2 16.5 10.5 16.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="12" cy="7.5" r="0.75" fill="currentColor" />
    </svg>
  );
};

/**
 * UmbrellaBotIcon
 * Represents the Umbrella-Bot Discord Gateway, AI Copilot & Automation Agent
 */
export const UmbrellaBotIcon: React.FC<IconProps> = ({ className = 'h-4 w-4', size }) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={size ? { width: size, height: size } : undefined}
    >
      {/* Umbrella Canopy Antenna at the top */}
      <path
        d="M12 2C10 2 8.5 3 8 4.5H16C15.5 3 14 2 12 2Z"
        fill="currentColor"
        fillOpacity="0.3"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M12 4.5V6.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      
      {/* Bot Head Chassis */}
      <rect
        x="3.5"
        y="6.5"
        width="17"
        height="13"
        rx="3.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      
      {/* Cyber Visor / Dual Optical Eyes */}
      <circle cx="8.5" cy="11.5" r="1.5" fill="currentColor" />
      <circle cx="15.5" cy="11.5" r="1.5" fill="currentColor" />
      
      {/* Visor HUD Waveform Line */}
      <path
        d="M7.5 15.5H9L10 14.5L11 16.5L12.5 14.5L13.5 16.5L14.5 15.5H16.5"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      
      {/* Side Audio / Radio Receiver Nodes */}
      <path d="M1.5 11V15M22.5 11V15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
};

/**
 * UmbrellaPluginIcon
 * Represents the Umbrella-Plugin Bytecode JAR & Hot-Reload Module Engine
 */
export const UmbrellaPluginIcon: React.FC<IconProps> = ({ className = 'h-4 w-4', size }) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={size ? { width: size, height: size } : undefined}
    >
      {/* Isometric / Cybernetic Plugin Package Cube */}
      <path
        d="M12 2.5L20 7V17L12 21.5L4 17V7L12 2.5Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M12 2.5V11.5M12 21.5V11.5M4 7L12 11.5L20 7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      
      {/* Left Face Umbrella Rib Stamp */}
      <path
        d="M6.5 10L10 12V16L6.5 14V10Z"
        fill="currentColor"
        fillOpacity="0.25"
      />
      
      {/* Right Face Socket Contact Dots */}
      <circle cx="15.5" cy="13.5" r="1" fill="currentColor" />
      <circle cx="17.5" cy="12.5" r="1" fill="currentColor" />
      <circle cx="15.5" cy="16" r="1" fill="currentColor" />
      <circle cx="17.5" cy="15" r="1" fill="currentColor" />
    </svg>
  );
};
