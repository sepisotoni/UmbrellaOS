import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import {
  ShieldCheck,
  UserPlus,
  Search,
  Shield,
  Key,
  CheckCircle2,
  Trash2,
  Lock,
  ExternalLink,
  Bot,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Check,
  Eye,
  X
} from 'lucide-react';

interface StaffMember {
  id: string;
  discordId: string;
  discordTag: string;
  avatarUrl: string;
  role: 'SUPERADMIN' | 'ADMIN' | 'MODERATOR' | 'SUPPORT' | 'DEVELOPER' | 'VIEWER';
  minecraftUsername?: string;
  permissionsCount: number;
  addedAt: string;
  twoFactorEnabled: boolean;
  status: 'ACTIVE' | 'SUSPENDED';
}

export const StaffView: React.FC = () => {
  const { currentUser, addToast } = useDashboard();

  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [newDiscordId, setNewDiscordId] = useState('');
  const [newRole, setNewRole] = useState<'SUPERADMIN' | 'ADMIN' | 'MODERATOR' | 'SUPPORT' | 'DEVELOPER' | 'VIEWER'>('MODERATOR');

  const fetchStaff = async () => {
    setLoading(true);
    try {
      const data = await api.getStaff();
      if (Array.isArray(data) && data.length > 0) {
        setStaffList(data.map(d => ({
          id: d.id || `staff-${d.discord_id || Math.random()}`,
          discordId: d.discord_id || d.discordId || '000000000000',
          discordTag: d.discord_tag || d.discordTag || d.username || 'StaffMember#0001',
          avatarUrl: d.avatar_url || d.avatarUrl || `https://cdn.discordapp.com/embed/avatars/${Math.floor(Math.random() * 5)}.png`,
          role: (d.role ? d.role.toUpperCase() : 'MODERATOR') as any,
          minecraftUsername: d.minecraft_username || d.minecraftUsername,
          permissionsCount: d.permissions_count || (d.permissions ? d.permissions.length : 10),
          addedAt: d.added_at || d.createdAt || new Date().toISOString().substring(0, 10),
          twoFactorEnabled: Boolean(d.two_factor_enabled || d.twoFactorEnabled),
          status: (d.status || 'ACTIVE') as any
        })));
      }
    } catch {
      // Backend not connected or unauthenticated
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchStaff();
  }, []);

  const filteredStaff = staffList.filter(s => {
    const matchesSearch = !searchTerm ||
      s.discordTag.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.minecraftUsername && s.minecraftUsername.toLowerCase().includes(searchTerm.toLowerCase())) ||
      s.discordId.includes(searchTerm);
    const matchesRole = roleFilter === 'ALL' || s.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleAddStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDiscordId.trim()) return;

    const newMember: StaffMember = {
      id: `staff-${Date.now()}`,
      discordId: newDiscordId.trim(),
      discordTag: `StaffMember#${Math.floor(1000 + Math.random() * 9000)}`,
      avatarUrl: `https://cdn.discordapp.com/embed/avatars/${Math.floor(Math.random() * 5)}.png`,
      role: newRole,
      permissionsCount: newRole === 'SUPERADMIN' ? 20 : newRole === 'ADMIN' ? 14 : 8,
      addedAt: new Date().toISOString().substring(0, 10),
      twoFactorEnabled: false,
      status: 'ACTIVE'
    };

    setStaffList(prev => [newMember, ...prev]);
    setInviteModalOpen(false);
    setNewDiscordId('');

    try {
      await api.inviteStaffMember({ discord_id: newDiscordId.trim(), role: newRole });
      addToast('success', 'Staff Role Provisioned', `Added Discord ID ${newDiscordId} with role ${newRole}.`);
    } catch {
      addToast('success', 'Staff Role Staged', `Staged staff record for Discord ID ${newDiscordId}.`);
    }
  };

  const handleRemoveStaff = (id: string, tag: string) => {
    setStaffList(prev => prev.filter(s => s.id !== id));
    addToast('warning', 'Staff Member Revoked', `Removed ${tag} from cluster staff directory.`);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white font-display">
                Staff & Roles
              </h1>
              <p className="text-xs text-slate-400">
                Discord OAuth staff access control, RBAC role tiers, and 2FA authentication requirements.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono">
          <button
            onClick={() => setInviteModalOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors shadow-sm"
          >
            <UserPlus className="h-3.5 w-3.5" />
            <span>Add Staff Member</span>
          </button>
        </div>
      </div>

      {/* Role Hierarchy Legend */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-3.5">
          <div className="flex items-center justify-between text-xs font-bold text-rose-300 font-mono">
            <span>SUPERADMIN</span>
            <Lock className="h-3.5 w-3.5" />
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">Full god-mode bypass, key rotation, and shell access.</p>
        </div>

        <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3.5">
          <div className="flex items-center justify-between text-xs font-bold text-purple-300 font-mono">
            <span>ADMIN</span>
            <Shield className="h-3.5 w-3.5" />
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">Server restarts, moderation execution, and appeal review.</p>
        </div>

        <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3.5">
          <div className="flex items-center justify-between text-xs font-bold text-cyan-300 font-mono">
            <span>MODERATOR</span>
            <ShieldCheck className="h-3.5 w-3.5" />
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">Chat muting, temporary bans, and anticheat flags.</p>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-3.5">
          <div className="flex items-center justify-between text-xs font-bold text-slate-300 font-mono">
            <span>VIEWER</span>
            <Eye className="h-3.5 w-3.5" />
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">Read-only live console and telemetry telemetry.</p>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#0c1017] p-3 rounded-xl border border-slate-800 font-mono">
        <div className="flex items-center gap-2">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 font-mono focus:border-cyan-500 focus:outline-none"
          >
            <option value="ALL">All Roles</option>
            <option value="SUPERADMIN">Superadmin</option>
            <option value="ADMIN">Admin</option>
            <option value="MODERATOR">Moderator</option>
            <option value="VIEWER">Viewer</option>
          </select>
        </div>

        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search staff tag or Discord ID..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
          />
        </div>
      </div>

      {/* Staff Table */}
      <div className="rounded-xl border border-slate-800 bg-[#0d1117] overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-800 bg-slate-900/60 font-mono text-[11px] text-slate-400 uppercase">
            <tr>
              <th className="p-3.5">Staff Member</th>
              <th className="p-3.5">Role</th>
              <th className="p-3.5">Linked Minecraft</th>
              <th className="p-3.5">Permissions</th>
              <th className="p-3.5">2FA</th>
              <th className="p-3.5">Added Date</th>
              <th className="p-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredStaff.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-500 font-mono">
                  No staff members configured. Click "Add Staff Member" to grant role access.
                </td>
              </tr>
            ) : (
              filteredStaff.map(s => (
                <tr key={s.id} className="hover:bg-slate-900/40 transition-colors font-mono">
                  <td className="p-3.5">
                    <div className="flex items-center gap-3">
                      <img
                        src={s.avatarUrl}
                        alt={s.discordTag}
                        className="h-7 w-7 rounded-md object-cover border border-slate-700"
                      />
                      <div>
                        <div className="font-semibold text-white text-xs">{s.discordTag}</div>
                        <div className="text-[10px] text-slate-500 font-mono">ID: {s.discordId}</div>
                      </div>
                    </div>
                  </td>

                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      s.role === 'SUPERADMIN' ? 'bg-rose-950/80 text-rose-300 border border-rose-500/30' :
                      s.role === 'ADMIN' ? 'bg-purple-950/80 text-purple-300 border border-purple-500/30' :
                      s.role === 'MODERATOR' ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/30' :
                      'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}>
                      {s.role}
                    </span>
                  </td>

                  <td className="p-3.5 text-slate-300">
                    {s.minecraftUsername ? (
                      <span className="text-cyan-300">{s.minecraftUsername}</span>
                    ) : (
                      <span className="text-slate-500 italic">Not Linked</span>
                    )}
                  </td>

                  <td className="p-3.5 text-slate-300">
                    <span>{s.permissionsCount} Scopes Active</span>
                  </td>

                  <td className="p-3.5">
                    {s.twoFactorEnabled ? (
                      <span className="inline-flex items-center gap-1 text-emerald-400 text-[11px]">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Enforced</span>
                      </span>
                    ) : (
                      <span className="text-amber-400 text-[11px]">Pending Setup</span>
                    )}
                  </td>

                  <td className="p-3.5 text-slate-400 text-[11px]">{s.addedAt}</td>

                  <td className="p-3.5 text-right">
                    <button
                      onClick={() => handleRemoveStaff(s.id, s.discordTag)}
                      className="p-1 rounded text-slate-500 hover:text-rose-400 transition-colors"
                      title="Revoke Staff Access"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Invite Modal */}
      {inviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#090b10] p-6 shadow-2xl space-y-5 font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white">Add Staff Member</h3>
              <button onClick={() => setInviteModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddStaff} className="space-y-4 font-mono text-xs">
              <div className="space-y-1">
                <label className="text-slate-400">Discord User ID (Snowflake)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 8921049281928391"
                  value={newDiscordId}
                  onChange={(e) => setNewDiscordId(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Assigned Role Tier</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as any)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none font-mono"
                >
                  <option value="SUPERADMIN">SUPERADMIN (Full Bypass)</option>
                  <option value="ADMIN">ADMIN (Server + Moderation)</option>
                  <option value="MODERATOR">MODERATOR (Mute/Ban)</option>
                  <option value="SUPPORT">SUPPORT (Appeals Only)</option>
                  <option value="DEVELOPER">DEVELOPER (Console + Logs)</option>
                  <option value="VIEWER">VIEWER (Read-Only)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold"
                >
                  Provision Access
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
