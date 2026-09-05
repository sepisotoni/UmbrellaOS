import React, { useState, useEffect, useMemo } from 'react';
import { api, StaffMember, DiscordGuildMember, RoleSchema } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  ShieldCheck,
  UserPlus,
  RefreshCw,
  AlertCircle,
  X,
  ChevronDown,
} from 'lucide-react';

export const StaffView: React.FC = () => {
  const { addToast } = useDashboard();
  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [discordMembers, setDiscordMembers] = useState<DiscordGuildMember[]>([]);
  const [roles, setRoles] = useState<RoleSchema[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [discordMembersFailed, setDiscordMembersFailed] = useState<boolean>(false);

  // Add staff modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [newDiscordId, setNewDiscordId] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('moderator');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchStaffData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [staffRes, discordRes, rolesRes] = await Promise.allSettled([
        api.getStaffMembers(),
        api.getDiscordGuildMembers(),
        api.getRoles(),
      ]);

      if (staffRes.status === 'fulfilled') {
        setStaffList(staffRes.value || []);
      } else {
        throw new Error('Failed to load staff roster');
      }

      if (discordRes.status === 'fulfilled') {
        setDiscordMembers(discordRes.value || []);
        setDiscordMembersFailed(false);
      } else {
        setDiscordMembers([]);
        setDiscordMembersFailed(true);
      }

      if (rolesRes.status === 'fulfilled') {
        const sorted = (rolesRes.value || []).sort((a, b) => {
          const order = ['owner', 'admin', 'moderator', 'helper', 'member'];
          return order.indexOf(a.name) - order.indexOf(b.name);
        });
        setRoles(sorted);
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

  const handlePromoteDemote = async (memberId: string, action: 'promote' | 'demote') => {
    try {
      const result = await api.manageStaff({ user_id: memberId, action });
      addToast({
        type: 'success',
        title: 'Staff Role Updated',
        message: `Role changed to ${(result?.new_role || action).toUpperCase()}.`,
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
      // TODO: core needs a POST /staff/deactivate endpoint — for now use promote/demote as placeholder
      addToast({ type: 'error', title: 'Not Implemented', message: 'Staff deactivation endpoint not yet available on core.' });
      return;
      await api.manageStaff({ user_id: memberId, is_active: !currentActive });
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
        role: newRole,
      });
      addToast({
        type: 'success',
        title: 'Staff Added',
        message: `Granted ${newRole.toUpperCase()} permissions.`,
      });
      setIsAddModalOpen(false);
      setNewDiscordId('');
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

  // Generic permission grouping (by dot-notation prefix, e.g.
  // "moderation.ban" -> group "moderation") — extracted from the
  // Appoint Staff modal's original inline logic so both the modal and
  // each staff card below can reuse it. Defined before groupedPerms
  // below since it's referenced inside that useMemo's callback, which
  // runs synchronously on first render.
  const groupPermissions = (permissions: string[] | undefined): Record<string, string[]> => {
    if (!permissions || permissions.length === 0) return {};
    const groups: Record<string, string[]> = {};
    for (const p of permissions) {
      const parts = p.split('.');
      const prefix = parts.length > 1 ? parts[0] : 'general';
      if (!groups[prefix]) groups[prefix] = [];
      groups[prefix].push(p);
    }
    return groups;
  };

  // Group permissions for the currently selected role in the appoint modal
  const selectedRoleObj = useMemo(() => {
    return roles.find((r) => r.name.toLowerCase() === newRole.toLowerCase());
  }, [roles, newRole]);

  const groupedPerms = useMemo(() => {
    return groupPermissions(selectedRoleObj?.permissions);
  }, [selectedRoleObj]);

  // AUDIT-2026-08-30: [HEAD]'s requested role color scheme named
  // OWNER/ADMIN/MODERATOR/SUPPORT/VIEWER, but the roles actually seeded
  // in this codebase (services/roles_service.py) are
  // owner/admin/moderator/helper/member — applying the same color
  // hierarchy to the real names (helper stands in for "support",
  // member for "viewer"). Falls back to slate for any custom role
  // created later that doesn't match one of these.
  const roleBadgeStyle = (role: string | null): string => {
    switch ((role || '').toLowerCase()) {
      case 'owner': return 'bg-purple-950/80 text-purple-300 border-purple-800/40';
      case 'admin': return 'bg-rose-950/80 text-rose-300 border-rose-800/40';
      case 'moderator': return 'bg-orange-950/80 text-orange-300 border-orange-800/40';
      case 'helper': return 'bg-sky-950/80 text-sky-300 border-sky-800/40';
      case 'member': return 'bg-slate-800/80 text-slate-300 border-slate-700/40';
      default: return 'bg-slate-800/80 text-slate-300 border-slate-700/40';
    }
  };

  // Which staff cards have their permission breakdown expanded —
  // collapsed by default per [HEAD]'s "overwhelming permissions column"
  // notice.
  const [expandedPerms, setExpandedPerms] = useState<Set<string>>(new Set());
  const togglePermsExpanded = (memberId: string) => {
    setExpandedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(memberId)) next.delete(memberId);
      else next.add(memberId);
      return next;
    });
  };

  const getStaffAvatar = (member: StaffMember) => {
    if (member.avatar_url) return member.avatar_url;
    const discordIdInt = Math.abs(parseInt(member.discord_id, 10) || 0);
    const avatarIndex = discordIdInt % 5;
    return `https://cdn.discordapp.com/embed/avatars/${avatarIndex}.png`;
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

      {/* Staff Roster — card grid per [HEAD]'s "cards instead of flat table" ask */}
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
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {staffList.map((member) => {
              const perms = member.permissions || [];
              const grouped = groupPermissions(perms);
              const categoryCount = Object.keys(grouped).length;
              const isExpanded = expandedPerms.has(member.id);
              return (
                <div
                  key={member.id}
                  className="rounded-xl border border-[#1e1b4b] bg-[#070914] p-4 flex flex-col gap-3 hover:border-purple-500/30 transition"
                >
                  {/* Identity row — Discord avatar prominent per [HEAD] */}
                  <div className="flex items-center gap-3">
                    <img
                      src={getStaffAvatar(member)}
                      alt={member.username || 'Staff'}
                      className="h-12 w-12 rounded-full border-2 border-purple-500/40 object-cover bg-purple-950/80 shrink-0"
                      onError={(e) => { (e.currentTarget as HTMLImageElement).src = 'https://cdn.discordapp.com/embed/avatars/0.png'; }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-bold text-white text-sm truncate">
                        {member.username || member.discord_id}
                      </div>
                      <div className="text-[11px] text-purple-300/80 font-mono truncate">{member.discord_id}</div>
                    </div>
                    <button
                      onClick={() => handleToggleActive(member.id, member.is_active)}
                      title="Click to toggle active status"
                      className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition border ${
                        member.is_active
                          ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/40 hover:bg-emerald-900/80'
                          : 'bg-rose-950/80 text-rose-300 border-rose-800/40 hover:bg-rose-900/80'
                      }`}
                    >
                      {member.is_active ? 'ACTIVE' : 'DISABLED'}
                    </button>
                  </div>

                  {/* Role — colored badge, doubles as the change-role control */}
                  <select
                    value={member.role || 'moderator'}
                    onChange={(e) => {
                      // AUDIT-2026-08-30 fix: this hierarchy previously read
                      // ["viewer","support","moderator","admin","owner"] —
                      // neither "viewer" nor "support" are real role names.
                      // The actual source of truth is
                      // services/staff_service.py::ROLE_LADDER =
                      // ["member","helper","moderator","admin","owner"].
                      // With the wrong array, indexOf("member")/indexOf("helper")
                      // both returned -1, so promote/demote direction was
                      // computed wrong (or silently defaulted to demote)
                      // for either of the two lowest real roles.
                      const ladder = ["member", "helper", "moderator", "admin", "owner"];
                      const ci = ladder.indexOf((member.role || "").toLowerCase());
                      const ni = ladder.indexOf(e.target.value.toLowerCase());
                      handlePromoteDemote(member.id, ni > ci ? "promote" : "demote");
                    }}
                    className={`w-full rounded-lg border px-2.5 py-1.5 text-xs font-bold cursor-pointer focus:outline-none ${roleBadgeStyle(member.role)}`}
                  >
                    {roles.length > 0 ? (
                      roles.map((r) => (
                        <option key={r.id} value={r.name}>{r.name.toUpperCase()}</option>
                      ))
                    ) : (
                      <option value="moderator">MODERATOR</option>
                    )}
                  </select>

                  {/* Permissions — collapsed summary by default per [HEAD]'s
                      "overwhelming permissions column" notice, grouped
                      chips on expand */}
                  <div className="rounded-lg border border-[#1e1b4b] bg-[#05091a] p-2.5">
                    <button
                      onClick={() => togglePermsExpanded(member.id)}
                      className="w-full flex items-center justify-between text-[11px] text-slate-400 hover:text-white transition cursor-pointer"
                    >
                      <span>
                        {perms.length > 0
                          ? `${perms.length} permission${perms.length === 1 ? '' : 's'} across ${categoryCount} categor${categoryCount === 1 ? 'y' : 'ies'}`
                          : 'Standard role permissions'}
                      </span>
                      {perms.length > 0 && (
                        <ChevronDown className={`h-3.5 w-3.5 shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                      )}
                    </button>
                    {isExpanded && perms.length > 0 && (
                      <div className="mt-2 space-y-1.5 max-h-40 overflow-y-auto">
                        {(Object.entries(grouped) as [string, string[]][]).map(([ns, groupPerms]) => (
                          <div key={ns}>
                            <span className="text-[9px] uppercase font-mono text-slate-500 font-bold block mb-1">{ns}</span>
                            <div className="flex flex-wrap gap-1">
                              {groupPerms.map((p) => (
                                <span
                                  key={p}
                                  className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/40"
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
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
                    }}
                    className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none mb-2"
                  >
                    <option value="">-- Choose from Discord Server Members --</option>
                    {discordMembers.map((m) => (
                      <option key={m.discord_id} value={m.discord_id}>
                        {m.username} ({m.discord_id})
                      </option>
                    ))}
                  </select>
                ) : discordMembersFailed ? (
                  <div className="mb-2 rounded-lg border border-amber-500/30 bg-amber-950/30 px-2.5 py-2 text-[11px] text-amber-300 flex items-start gap-1.5">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                    <span>
                      Could not load Discord server members (Discord bot token/guild ID may not be
                      configured, or you may not have permission). Falling back to manual entry.
                    </span>
                  </div>
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
                  {roles.length > 0 ? (
                    roles.map((r) => (
                      <option key={r.id} value={r.name}>
                        {r.name.toUpperCase()}
                      </option>
                    ))
                  ) : (
                    <option value="moderator">MODERATOR</option>
                  )}
                </select>
                {selectedRoleObj?.description && (
                  <p className="text-[11px] text-slate-400 mt-1 italic">
                    {selectedRoleObj.description}
                  </p>
                )}
              </div>

              {/* Resolved Permissions Preview */}
              {selectedRoleObj && (
                <div className="rounded-lg border border-[#1e1b4b] bg-[#070914] p-3 space-y-2 max-h-36 overflow-y-auto">
                  <div className="text-[10px] font-mono uppercase text-slate-400 font-semibold">
                    Granted Permissions ({selectedRoleObj.permissions?.length || 0})
                  </div>
                  {(Object.entries(groupedPerms) as [string, string[]][]).map(([ns, perms]) => (
                    <div key={ns} className="space-y-1">
                      <span className="text-[9px] uppercase font-mono text-slate-500 font-bold block">{ns}</span>
                      <div className="flex flex-wrap gap-1">
                        {perms.map((p) => (
                          <span
                            key={p}
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/40"
                          >
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

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
