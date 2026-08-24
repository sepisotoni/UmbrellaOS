import React, { useState, useEffect } from 'react';
import { api, StaffMember, DiscordGuildMember } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  ShieldCheck,
  UserPlus,
  RefreshCw,
  AlertCircle,
  Shield,
  Trash2,
  CheckCircle2,
  X,
  User,
  ExternalLink,
} from 'lucide-react';

export const StaffView: React.FC = () => {
  const { addToast } = useDashboard();
  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [discordMembers, setDiscordMembers] = useState<DiscordGuildMember[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Add staff modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [newDiscordId, setNewDiscordId] = useState<string>('');
  const [newUsername, setNewUsername] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('moderator');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchStaffData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [staffRes, discordRes] = await Promise.allSettled([
        api.getStaffMembers(),
        api.getDiscordGuildMembers(),
      ]);

      if (staffRes.status === 'fulfilled') {
        setStaffList(staffRes.value || []);
      } else {
        throw new Error('Failed to load staff roster');
      }

      if (discordRes.status === 'fulfilled') {
        setDiscordMembers(discordRes.value || []);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch staff roster');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStaffData();
  }, []);

  const handlePromoteDemote = async (memberId: string, role: string) => {
    try {
      await api.manageStaff({ member_id: memberId, role });
      addToast({
        type: 'success',
        title: 'Staff Role Updated',
        message: `Role changed to ${role.toUpperCase()}.`,
      });
      fetchStaffData();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Role Update Failed',
        message: err.message,
      });
    }
  };

  const handleToggleActive = async (memberId: string, currentActive: boolean) => {
    try {
      await api.manageStaff({ member_id: memberId, is_active: !currentActive });
      addToast({
        type: 'success',
        title: 'Status Updated',
        message: `Staff member set to ${!currentActive ? 'Active' : 'Disabled'}.`,
      });
      fetchStaffData();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Update Failed',
        message: err.message,
      });
    }
  };

  const handleAddStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDiscordId.trim()) return;

    setIsSubmitting(true);
    try {
      await api.addStaffMember({
        discord_id: newDiscordId.trim(),
        username: newUsername.trim() || undefined,
        role: newRole,
      });
      addToast({
        type: 'success',
        title: 'Staff Added',
        message: `Granted ${newRole.toUpperCase()} permissions.`,
      });
      setIsAddModalOpen(false);
      setNewDiscordId('');
      setNewUsername('');
      fetchStaffData();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Failed to Add Staff',
        message: err.message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id="umbrella-staff-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Staff Roster & Permissions</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {staffList.length} Appointed
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage administrative access, moderator appointments, and Discord synchronization.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="add-staff-btn"
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-purple-500 transition cursor-pointer shadow-[0_0_12px_rgba(168,85,247,0.3)]"
          >
            <UserPlus className="h-3.5 w-3.5" />
            <span>Appoint Staff</span>
          </button>

          <button
            id="staff-refresh-btn"
            onClick={fetchStaffData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading staff data:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Staff Roster Table */}
      <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            Loading staff roster from core...
          </div>
        ) : staffList.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            No staff members found. Appoint staff via the button above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1e1b4b] text-slate-400">
                  <th className="pb-3 font-semibold">Staff Member</th>
                  <th className="pb-3 font-semibold">Discord ID</th>
                  <th className="pb-3 font-semibold">Role</th>
                  <th className="pb-3 font-semibold">Permissions</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e1b4b]/60">
                {staffList.map((member) => (
                  <tr key={member.id} className="hover:bg-[#121638]/50 transition">
                    <td className="py-3 font-bold text-white flex items-center gap-2">
                      {member.avatar_url ? (
                        <img
                          src={member.avatar_url}
                          alt={member.username}
                          className="h-6 w-6 rounded-full border border-purple-500/40 object-cover"
                        />
                      ) : (
                        <div className="h-6 w-6 rounded-full bg-purple-900/60 border border-purple-500/40 flex items-center justify-center text-[10px] text-purple-300">
                          {member.username ? member.username.charAt(0).toUpperCase() : 'S'}
                        </div>
                      )}
                      <span>{member.username || 'Staff'}</span>
                    </td>
                    <td className="py-3 text-purple-300 font-mono">{member.discord_id}</td>
                    <td className="py-3">
                      <select
                        value={member.role || 'moderator'}
                        onChange={(e) => handlePromoteDemote(member.id, e.target.value)}
                        className="rounded border border-[#1e1b4b] bg-[#070914] px-2 py-1 text-xs text-white focus:border-purple-500 focus:outline-none"
                      >
                        <option value="moderator">Moderator</option>
                        <option value="senior_mod">Senior Mod</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                      </select>
                    </td>
                    <td className="py-3 text-slate-400">
                      {member.permissions && member.permissions.length > 0
                        ? member.permissions.join(', ')
                        : 'Standard Role Perms'}
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => handleToggleActive(member.id, member.is_active)}
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition ${
                          member.is_active
                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40 hover:bg-emerald-900/80'
                            : 'bg-rose-950/80 text-rose-300 border border-rose-800/40 hover:bg-rose-900/80'
                        }`}
                      >
                        {member.is_active ? 'ACTIVE' : 'DISABLED'}
                      </button>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleToggleActive(member.id, true)}
                        className="text-[11px] text-slate-400 hover:text-rose-400 underline cursor-pointer"
                      >
                        Deactivate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Appoint Staff */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-[#1e1b4b] bg-[#0d1127] p-6 shadow-2xl space-y-5 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-purple-400" />
                <span>Appoint Network Staff</span>
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddStaff} className="space-y-4">
              <div>
                <label className="block text-slate-300 mb-1">Discord User ID or Select Member</label>
                {discordMembers.length > 0 ? (
                  <select
                    value={newDiscordId}
                    onChange={(e) => {
                      setNewDiscordId(e.target.value);
                      const selected = discordMembers.find((m) => m.id === e.target.value);
                      if (selected) setNewUsername(selected.username);
                    }}
                    className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none mb-2"
                  >
                    <option value="">-- Choose from Discord Server Members --</option>
                    {discordMembers.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.username} ({m.id})
                      </option>
                    ))}
                  </select>
                ) : null}

                <input
                  type="text"
                  value={newDiscordId}
                  onChange={(e) => setNewDiscordId(e.target.value)}
                  placeholder="Or enter Discord ID manually (e.g. 123456789012345678)"
                  required
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Appointed Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                >
                  <option value="moderator">Moderator</option>
                  <option value="senior_mod">Senior Mod</option>
                  <option value="admin">Administrator</option>
                  <option value="owner">Network Owner</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="flex-1 py-2 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2 rounded-lg border border-purple-500/50 bg-purple-600 hover:bg-purple-500 text-white font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Appointing...' : 'Confirm Appointment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
