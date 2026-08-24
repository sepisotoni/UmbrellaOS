import React from 'react';
import { ShieldX, LogOut, Mail, ArrowLeft, Lock, UserCheck, AlertOctagon, HelpCircle } from 'lucide-react';
import { useDashboard, NavigationTab } from '../../context/DashboardContext';
import { UmbrellaLogo } from '../common/UmbrellaLogo';

interface AccessDeniedViewProps {
  attemptedTab?: NavigationTab | string;
  requiredRole?: string;
  noRole?: boolean;
}

export const AccessDeniedView: React.FC<AccessDeniedViewProps> = ({
  attemptedTab,
  requiredRole,
  noRole,
}) => {
  const { currentUser, logout, setActiveTab } = useDashboard();

  return (
    <div
      id="umbrella-access-denied-page"
      className="min-h-[85vh] flex flex-col items-center justify-center p-6 text-center select-none"
    >
      <div className="w-full max-w-xl space-y-6">
        {/* Security Shield Visual */}
        <div className="flex justify-center items-center">
          <div className="relative">
            <div className="absolute -inset-4 rounded-full bg-rose-500/20 blur-2xl animate-pulse" />
            <div className="relative h-20 w-20 rounded-3xl border border-rose-500/40 bg-[#0c050b]/90 backdrop-blur-xl flex items-center justify-center shadow-[0_0_30px_rgba(244,63,94,0.3)]">
              <ShieldX className="h-10 w-10 text-rose-400" />
              <div className="absolute -top-1 -right-1 h-3.5 w-3.5 rounded-full bg-amber-500 border-2 border-[#0c050b]" />
            </div>
          </div>
        </div>

        {/* Access Denied Header */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-rose-500/30 bg-rose-950/50 text-[11px] font-mono text-rose-300">
            <AlertOctagon className="h-3.5 w-3.5 text-rose-400" />
            <span>HTTP 403 • RESTRICTED SECURITY ZONE</span>
          </div>

          <h1 className="text-3xl font-extrabold text-white tracking-tight font-sans">
            Access Denied
          </h1>

          <p className="text-sm text-slate-300 max-w-md mx-auto leading-relaxed font-sans">
            {noRole ? (
              <>
                Your Discord account is not authorized to access{' '}
                <span className="font-mono text-rose-300 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/40">
                  Umbrella Dashboard
                </span>
                . You must be assigned a staff role by an administrator before you can log in.
              </>
            ) : (
              <>
                Your authenticated staff credentials lack the security clearance required to inspect{' '}
                {attemptedTab ? (
                  <span className="font-mono text-rose-300 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/40">
                    "{attemptedTab}"
                  </span>
                ) : (
                  'this restricted system section'
                )}
                .
              </>
            )}
          </p>
        </div>

        {/* Authenticated Identity Dossier Card */}
        <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/90 backdrop-blur-xl p-5 text-left space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#141d3d] pb-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-indigo-950 border border-indigo-500/40 flex items-center justify-center font-bold text-indigo-300 text-sm">
                {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
              </div>
              <div>
                <div className="text-sm font-bold text-white flex items-center gap-2">
                  <span>@{currentUser?.username || 'Unknown'}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-mono font-bold bg-rose-950/80 text-rose-300 border border-rose-800/50">
                    {currentUser?.role ? currentUser.role.toUpperCase() : 'NO ROLE'}
                  </span>
                </div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">
                  Discord ID: {currentUser?.discord_id || 'Not Linked'}
                </div>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[10px] uppercase font-mono text-slate-500 block">STATUS</span>
              <span className="inline-flex items-center gap-1 text-xs font-mono font-semibold text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Authenticated
              </span>
            </div>
          </div>

          {/* Permissions / Clearance Details */}
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center text-slate-400">
              <span>Required Clearance:</span>
              <span className="text-amber-300 font-bold">
                {noRole ? 'ANY STAFF ROLE' : requiredRole ? requiredRole.toUpperCase() : 'ADMINISTRATOR / SUPERADMIN'}
              </span>
            </div>

            <div className="flex justify-between items-center text-slate-400">
              <span>Assigned Role:</span>
              <span className="text-slate-300">
                {currentUser?.role ? currentUser.role : 'None — contact an administrator'}
              </span>
            </div>
          </div>

          {/* Help box */}
          <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-3 text-xs text-slate-300 leading-relaxed font-sans flex items-start gap-2.5">
            <HelpCircle className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              {noRole
                ? <>To request dashboard access, contact the server owner on Discord with your Discord ID: <span className="text-indigo-300 font-mono select-all">{currentUser?.discord_id || 'N/A'}</span>.</>
                : <>To request a role elevation or permission update, contact a Superadmin on Discord with your Discord ID (<span className="text-indigo-300 font-mono select-all">{currentUser?.discord_id || 'N/A'}</span>).</>
              }
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row justify-center items-center gap-3 pt-2">
          {!noRole && (
            <button
              onClick={() => setActiveTab('overview')}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-600 hover:bg-indigo-500 px-6 py-2.5 text-xs font-bold text-white transition shadow-[0_0_15px_rgba(99,102,241,0.3)] cursor-pointer"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Return to Permitted Overview</span>
            </button>
          )}

          <button
            onClick={logout}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/60 px-5 py-2.5 text-xs font-bold text-rose-300 hover:text-white transition cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            <span>{noRole ? 'Sign Out' : 'Switch Staff Account'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
