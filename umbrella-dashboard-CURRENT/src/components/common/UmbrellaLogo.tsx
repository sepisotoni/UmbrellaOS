import React from 'react';
import {
  BrandLogo,
  BrandLogoVariant,
  LogoSize,
  LogoRenderMode,
  BRAND_DEFINITIONS,
} from './BrandLogos';

interface UmbrellaLogoProps {
  variant?: BrandLogoVariant;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  renderMode?: LogoRenderMode;
  showWordmark?: boolean;
  className?: string;
  subtext?: string;
}

export const UmbrellaLogo: React.FC<UmbrellaLogoProps> = ({
  variant = 'os',
  size = 'md',
  renderMode = 'vector',
  showWordmark = true,
  className = '',
  subtext,
}) => {
  return (
    <BrandLogo
      variant={variant}
      size={size as LogoSize}
      renderMode={renderMode}
      showWordmark={showWordmark}
      showBadge={false}
      className={className}
      subtext={subtext}
      glow={true}
    />
  );
};

export { UmbrellaCoreIcon, UmbrellaBotIcon, UmbrellaPluginIcon } from './UmbrellaIcons';
export { BrandLogo, BRAND_DEFINITIONS } from './BrandLogos';
export type { BrandLogoVariant, LogoSize, LogoRenderMode } from './BrandLogos';
