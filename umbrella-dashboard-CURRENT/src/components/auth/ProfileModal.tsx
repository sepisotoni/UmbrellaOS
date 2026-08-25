import React, { useState, useMemo } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import { X, Copy, Check, LogOut } from 'lucide-react';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({ isOpen, onClose }) => {
  const { currentUser, setCurrentUser, setSessionToken, setActiveTab, healthInfo, addToast } = useDashboard();
  const [copiedId, setCopiedId] = useState(false);

  const groupedPermissions = useMemo(() => {
    if (!currentUser?.permissions) return {};
    const groups: Record<string, string[]> = {};
    for (const perm of currentUser.permissions) {
      const parts = perm.split('.');
      const prefix = parts.length > 1 ? parts[0] : 'general';
      if (!groups[prefix]) groups[prefix] = [];
      groups[prefix].push(perm);
    }
    return groups;
  }, [currentUser?.permissions]);

  if (!isOpen || !currentUser) return null;

  const handleCopyDiscordId = () => {
    if (currentUser.discord_id) {
      navigator.clipboard.writeText(currentUser.discord_id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handleSignOut = () => {
    api.logout();
    setCurrentUser(null);
    setSessionToken(null);
    setActiveTab('login');
    addToast({
      type: 'info',
      title: 'Signed Out',
      message: 'You have been logged out of UmbrellaOS.',
    });
    onClose();
  };

  const fallbackAvatar = `https://cdn.discordapp.com/embed/avatars/${Math.abs(parseInt(currentUser.discord_id, 10) || 0) % 5}.png`;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-[#141d3d] bg-[#060b1c] p-6 shadow-2xl space-y-5 text-slate-100 font-sans">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#141d3d] pb-3">
          <h3 className="font-bold text-white text-sm">Your Profile</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* User Identity & Sign Out */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {currentUser.avatar_url ? (
              <img
                src={currentUser.avatar_url}
                alt={currentUser.username}
                className="h-12 w-12 rounded-full border border-indigo-500/40 object-cover"
                onError={(e) => { (e.currentTarget as HTMLImageElement).src = fallbackAvatar; }}
              />
            ) : (
              <div className="h-12 w-12 rounded-full bg-indigo-950/80 border border-indigo-500/40 flex items-center justify-center font-bold text-indigo-200 text-lg">
                {currentUser.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
              </div>
            )}
            <div>
              <div className="font-bold text-white text-sm">{currentUser.username}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/40 font-semibold">
                  {currentUser.role || 'Member'}
                </span>
                <span className="text-[11px] text-slate-400">Authenticated via Discord</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleSignOut}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-950/40 hover:bg-rose-900/60 px-3 py-1.5 text-xs font-medium text-rose-300 hover:text-white transition cursor-pointer"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Sign out</span>
          </button>
        </div>

        {/* Discord ID */}
        <div className="rounded-xl border border-[#141d3d] bg-[#070914] p-3 flex items-center justify-between gap-2">
          <div>
            <div className="text-[10px] uppercase font-mono text-slate-500">Discord ID</div>
            <div className="text-xs font-mono text-indigo-300">{currentUser.discord_id}</div>
          </div>
          <button
            onClick={handleCopyDiscordId}
            className="p-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] text-slate-400 hover:text-white transition cursor-pointer"
            title="Copy Discord ID"
          >
            {copiedId ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>

        {/* Resolved RBAC Permissions */}
        <div className="space-y-2">
          <div className="text-[10px] font-mono uppercase text-slate-400 font-semibold">
            RESOLVED RBAC PERMISSIONS ({currentUser.permissions?.length || 0})
          </div>
          <div className="rounded-xl border border-[#141d3d] bg-[#070914] p-3 max-h-48 overflow-y-auto space-y-2">
            {Object.entries(groupedPermissions).length === 0 ? (
              <span className="text-xs text-slate-500 font-mono">No explicit permissions assigned</span>
            ) : (
              Object.entries(groupedPermissions).map(([ns, perms]) => (
                <div key={ns} className="space-y-1">
                  <div className="text-[9px] uppercase font-mono text-slate-600 font-bold">{ns}</div>
                  <div className="flex flex-wrap gap-1">
                    {perms.map((perm) => (
                      <span
                        key={perm}
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/30"
                      >
                        {perm}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Version Footer */}
        <div className="border-t border-[#141d3d] pt-3 text-center text-[11px] font-mono text-slate-500">
          UmbrellaOS Core v{healthInfo?.version || '1.0.0'}
        </div>
      </div>
    </div>
  );
};
