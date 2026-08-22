import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { UploadPluginModal } from '../modals/UploadPluginModal';
import { UmbrellaPluginIcon } from '../common/UmbrellaIcons';
import {
  Package,
  Search,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Activity,
  Shield,
  Radio,
  Server,
  Zap,
  Clock,
  Code2,
  Sliders,
  Check,
  Upload,
  Play,
  Pause,
  Trash2,
  Layers,
  Settings,
  Sparkles,
  Info
} from 'lucide-react';

export const PluginsView: React.FC = () => {
  const {
    connectedPluginHeartbeats,
    plugins,
    servers,
    refreshBackendData,
    togglePlugin,
    uninstallPlugin,
    updatePluginConfig,
    addToast
  } = useDashboard();

  const [activeSubTab, setActiveSubTab] = useState<'heartbeats' | 'catalog'>('heartbeats');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Config hot-editor state
  const [editingPluginId, setEditingPluginId] = useState<string | null>(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refreshBackendData();
    setIsRefreshing(false);
    addToast('success', 'Heartbeats Refreshed', 'Queried GET /api/v1/dashboard/plugins.');
  };

  const filteredHeartbeats = connectedPluginHeartbeats.filter(hb => {
    const matchesSearch = !searchTerm || 
      hb.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
      (hb.serverName && hb.serverName.toLowerCase().includes(searchTerm.toLowerCase())) ||
      hb.serverId.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'ALL' || hb.name === filterType;
    return matchesSearch && matchesType;
  });

  const filteredPlugins = plugins.filter(p => {
    const matchesSearch = !searchTerm ||
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.author.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = filterType === 'ALL' || p.category === filterType;
    return matchesSearch && matchesCategory;
  });

  const healthyCount = connectedPluginHeartbeats.filter(h => h.status === 'healthy').length;
  const avgPing = Math.round(
    connectedPluginHeartbeats.reduce((acc, h) => acc + h.heartbeatMs, 0) / (connectedPluginHeartbeats.length || 1)
  );

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <UmbrellaPluginIcon className="h-6 w-6 text-cyan-400" />
            <h1 className="text-xl font-bold tracking-tight text-white font-display">Plugin Management & Bridge Telemetry</h1>
            <span className="rounded-full bg-cyan-950/80 border border-cyan-500/30 px-2.5 py-0.5 text-xs font-mono font-bold text-cyan-300">
              Bridge v3.2
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Monitor real-time Java plugin heartbeats, deploy new .JAR archives, and manage hot-reload configurations across nodes.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md hover:from-cyan-500 hover:to-blue-500 transition-all cursor-pointer"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Upload Plugin (.jar)</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors font-mono cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* Real-time Status Metric Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono">
        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Healthy Bridge Heartbeats</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">{healthyCount}</span>
            <span className="text-xs text-slate-500 font-mono">/ {connectedPluginHeartbeats.length} check-ins</span>
          </div>
          <div className="mt-2 text-[11px] text-emerald-400 font-mono">100% Java Bridge fidelity</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Avg Bridge Latency</span>
            <Activity className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">{avgPing || 0}ms</span>
            <span className="text-xs text-emerald-400 font-mono">● Low Overheads</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 font-mono">Zero daemon overhead (In-JVM)</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Installed Packages</span>
            <Layers className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {plugins.filter(p => p.installed).length}
            </span>
            <span className="text-xs text-slate-500 font-mono">JARs mounted</span>
          </div>
          <div className="mt-2 text-[11px] text-cyan-400 font-mono">Paper & Purpur Compatible</div>
        </div>
      </div>

      {/* View Mode Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 font-sans">
        <button
          onClick={() => { setActiveSubTab('heartbeats'); setFilterType('ALL'); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeSubTab === 'heartbeats'
              ? 'bg-slate-800 text-cyan-300 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Radio className="h-3.5 w-3.5 text-cyan-400" />
          <span>Live Heartbeats & Check-Ins ({connectedPluginHeartbeats.length})</span>
        </button>

        <button
          onClick={() => { setActiveSubTab('catalog'); setFilterType('ALL'); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeSubTab === 'catalog'
              ? 'bg-slate-800 text-cyan-300 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Package className="h-3.5 w-3.5 text-cyan-400" />
          <span>Installed Plugin Registry & Config ({plugins.length})</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 font-sans">
        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
          {activeSubTab === 'heartbeats' ? (
            (['ALL', 'UmbrellaOS', 'GrimAC'] as const).map(type => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer whitespace-nowrap font-mono ${
                  filterType === type
                    ? 'bg-cyan-600 text-white shadow-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {type === 'ALL' ? 'All Heartbeats' : type}
              </button>
            ))
          ) : (
            (['ALL', 'Core Infrastructure', 'Security', 'World Management', 'Moderation'] as const).map(cat => (
              <button
                key={cat}
                onClick={() => setFilterType(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer whitespace-nowrap ${
                  filterType === cat
                    ? 'bg-cyan-600 text-white shadow-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat === 'ALL' ? 'All Categories' : cat}
              </button>
            ))
          )}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={activeSubTab === 'heartbeats' ? "Search heartbeats..." : "Search installed plugins..."}
            className="w-full rounded-lg border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none font-sans"
          />
        </div>
      </div>

      {/* SubTab 1: Heartbeats */}
      {activeSubTab === 'heartbeats' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredHeartbeats.length === 0 ? (
            <div className="col-span-2 p-8 rounded-xl border border-slate-800 bg-[#0d1117] text-center text-xs text-slate-500 font-mono">
              No plugin heartbeats received matching current filter. Deploy umbrella-plugin.jar to your server nodes.
            </div>
          ) : (
            filteredHeartbeats.map(hb => {
              const isGrim = hb.name === 'GrimAC';
              return (
                <div
                  key={hb.id}
                  className="rounded-xl border border-slate-800 bg-[#0d1117] p-5 space-y-4 hover:border-slate-700 transition-all shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${
                        isGrim
                          ? 'border-emerald-500/30 bg-emerald-950/40 text-emerald-400'
                          : 'border-cyan-500/30 bg-cyan-950/40 text-cyan-400'
                      }`}>
                        {isGrim ? <Shield className="h-5 w-5" /> : <Radio className="h-5 w-5" />}
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          {hb.name}
                          <span className="font-mono text-[10px] text-slate-400 font-normal">
                            ({hb.version})
                          </span>
                        </h3>
                        <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400 font-mono">
                          <Server className="h-3 w-3 text-slate-500" />
                          <span>{hb.serverName || hb.serverId}</span>
                        </div>
                      </div>
                    </div>

                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono border font-semibold ${
                      hb.status === 'healthy' ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30' :
                      hb.status === 'stale' ? 'bg-amber-950/60 text-amber-400 border-amber-500/30' :
                      'bg-rose-950/60 text-rose-400 border-rose-500/30'
                    }`}>
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      {hb.status.toUpperCase()}
                    </span>
                  </div>

                  {/* Heartbeat Telemetry */}
                  <div className="grid grid-cols-2 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs font-mono">
                    <div>
                      <span className="text-slate-500 text-[11px]">Heartbeat Latency:</span>
                      <div className="text-cyan-300 font-bold mt-0.5">{hb.heartbeatMs} ms</div>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[11px]">Last Check-In:</span>
                      <div className="text-slate-300 mt-0.5">{hb.lastSeen}</div>
                    </div>
                  </div>

                  {/* Active Features list */}
                  {hb.activeFeatures && hb.activeFeatures.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
                        Active Handlers ({hb.activeFeatures.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {hb.activeFeatures.map(f => (
                          <span
                            key={f}
                            className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono text-[10px] text-slate-300 flex items-center gap-1"
                          >
                            <Check className="h-2.5 w-2.5 text-cyan-400" />
                            {f}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* SubTab 2: Installed Plugins Catalog */}
      {activeSubTab === 'catalog' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans">
          {filteredPlugins.length === 0 ? (
            <div className="col-span-2 p-8 rounded-xl border border-slate-800 bg-[#0d1117] text-center text-xs text-slate-500 font-mono">
              No plugins match your filter. Click "Upload Plugin (.jar)" to deploy new bytecode packages.
            </div>
          ) : (
            filteredPlugins.map(plugin => {
              const isEditing = editingPluginId === plugin.id;
              return (
                <div
                  key={plugin.id}
                  className="rounded-xl border border-slate-800 bg-[#0d1117] p-5 space-y-4 hover:border-slate-700 transition-all shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
                        <Package className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          {plugin.name}
                          <span className="font-mono text-[10px] text-slate-400 font-normal">
                            v{plugin.version}
                          </span>
                        </h3>
                        <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400">
                          <span>by {plugin.author}</span>
                          <span>•</span>
                          <span className="font-mono text-cyan-400">{plugin.sizeKb} KB</span>
                          <span>•</span>
                          <span className="text-slate-500">{plugin.category}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => togglePlugin(plugin.id)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer border ${
                          plugin.enabled
                            ? 'bg-emerald-950/50 text-emerald-400 border-emerald-500/40 hover:bg-emerald-900/50'
                            : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                        }`}
                      >
                        {plugin.enabled ? (
                          <>
                            <Play className="h-3 w-3 fill-emerald-400" />
                            <span>Active</span>
                          </>
                        ) : (
                          <>
                            <Pause className="h-3 w-3" />
                            <span>Disabled</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-2">
                    {plugin.description}
                  </p>

                  {/* Resource Usage & Sandbox */}
                  <div className="grid grid-cols-3 gap-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 text-xs font-mono">
                    <div>
                      <span className="text-slate-500 text-[10px]">CPU:</span>
                      <div className="text-slate-200 font-bold">{plugin.resourceUsage?.avgCpuPercent || 0.1}%</div>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px]">Heap RAM:</span>
                      <div className="text-slate-200 font-bold">{plugin.resourceUsage?.memoryMb || 16} MB</div>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px]">Events/s:</span>
                      <div className="text-slate-200 font-bold">{plugin.resourceUsage?.eventsPerSec || 0}</div>
                    </div>
                  </div>

                  {/* Config Editor Toggle */}
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <button
                      onClick={() => setEditingPluginId(isEditing ? null : plugin.id)}
                      className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5 cursor-pointer"
                    >
                      <Settings className="h-3.5 w-3.5" />
                      <span>{isEditing ? 'Close Config Hot-Reload' : 'Live Config Editor'}</span>
                    </button>

                    <button
                      onClick={() => uninstallPlugin(plugin.id)}
                      className="text-xs text-slate-500 hover:text-rose-400 flex items-center gap-1 cursor-pointer transition-colors"
                      title="Uninstall plugin package"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      <span>Uninstall</span>
                    </button>
                  </div>

                  {/* Inline Live Config Editor */}
                  {isEditing && plugin.configEntries && (
                    <div className="p-3 rounded-lg border border-cyan-500/30 bg-slate-950 space-y-2.5 font-mono text-xs animate-in fade-in duration-100">
                      <div className="text-[11px] text-cyan-300 font-semibold flex items-center justify-between">
                        <span>Config Properties (config.yml)</span>
                        <span className="text-[10px] text-slate-400 font-normal">Hot-applied via Bridge</span>
                      </div>
                      {Object.entries(plugin.configEntries).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between gap-2">
                          <span className="text-slate-400 text-[11px]">{key}:</span>
                          {typeof val === 'boolean' ? (
                            <button
                              type="button"
                              onClick={() => updatePluginConfig(plugin.id, key, !val)}
                              className={`px-2 py-0.5 rounded text-[11px] font-bold border cursor-pointer ${
                                val ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40' : 'bg-slate-900 text-slate-400 border-slate-800'
                              }`}
                            >
                              {val ? 'TRUE' : 'FALSE'}
                            </button>
                          ) : (
                            <input
                              type="text"
                              defaultValue={String(val)}
                              onBlur={(e) => updatePluginConfig(plugin.id, key, e.target.value)}
                              className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs text-white focus:border-cyan-500 focus:outline-none w-36 text-right"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Architecture Note */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 text-xs text-slate-400 flex items-start gap-3 font-mono">
        <Info className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-200">Architecture Specification:</span> UmbrellaOS operates via the in-JVM <code className="font-mono text-cyan-300">umbrella-core-bridge.jar</code> plugin mounted directly on Paper, Purpur, Folia, and Velocity proxies. Telemetry, anticheat events, and commands communicate natively over local IPC and REST without running any host systemd daemons.
        </div>
      </div>

      {/* Upload Plugin Modal */}
      <UploadPluginModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
      />
    </div>
  );
};
