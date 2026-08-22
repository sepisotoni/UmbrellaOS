import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { NodeInfrastructure, MinecraftServer } from '../../types/dashboard';
import {
  Network,
  Server,
  Radio,
  Cpu,
  HardDrive,
  Activity,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  SlidersHorizontal,
  Terminal,
  Database,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Globe
} from 'lucide-react';

export const TopologyView: React.FC = () => {
  const { nodes, servers, setSelectedServerId, setActiveTab, restartServer, addToast } = useDashboard();
  const [selectedNodeId, setSelectedNodeId] = useState<string>(nodes[0]?.id || 'node-01');
  const [filterRegion, setFilterRegion] = useState<string>('ALL');

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || nodes[0];
  const assignedServers = servers.filter(s => selectedNode?.assignedServers?.includes(s.id));

  const filteredNodes = filterRegion === 'ALL' 
    ? nodes 
    : nodes.filter(n => n.region.toLowerCase().includes(filterRegion.toLowerCase()));

  const handleDrainNode = (nodeId: string) => {
    addToast('warning', 'Node Drainage Initiated', `Gracefully evacuating players from ${nodeId} to standby proxy routes.`);
  };

  const handleRestartPlugin = (nodeId: string) => {
    addToast('info', 'Plugin Restart Queued', `Umbrella plugin on ${nodeId} will reload on next heartbeat cycle.`);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Bar Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight font-display">
                Cluster Topology & Infrastructure Matrix
              </h1>
              <p className="text-xs text-slate-400">
                Interactive map of baremetal compute hosts, Velocity Edge Proxies, and Postgres/Redis Data Plane
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-medium font-mono">Filter Region:</span>
          <div className="flex items-center rounded-lg border border-slate-800 bg-slate-900/80 p-0.5 text-xs font-mono">
            {['ALL', 'us-east-1', 'eu-central-1'].map(region => (
              <button
                key={region}
                onClick={() => setFilterRegion(region)}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
                  filterRegion === region
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {region}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Visual Architectural Data Flow Map */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 shadow-lg relative overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-6">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            <Radio className="h-4 w-4 text-cyan-400" />
            <span>Real-time Layer Traffic & Ingress Pipeline</span>
          </div>
          <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Live Ingress Active
          </span>
        </div>

        {/* 3-Tier Layer Representation */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative">
          {/* Layer 1: Edge Proxies (Velocity) */}
          <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-cyan-300">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-cyan-400" />
                <span>Tier 1: Velocity Edge Proxies</span>
              </div>
              <span className="font-mono text-[10px] bg-cyan-950/80 border border-cyan-500/30 px-2 py-0.5 rounded text-cyan-300">
                Edge Ingress
              </span>
            </div>

            <div className="space-y-2">
              {servers.filter(s => s.type === 'velocity_proxy').length === 0 ? (
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-400">
                  <div className="font-semibold text-white">Velocity Primary Proxy</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">play.umbrella-mc.net:25565 • Modern Forwarding</div>
                </div>
              ) : (
                servers.filter(s => s.type === 'velocity_proxy').map(proxy => (
                  <div 
                    key={proxy.id}
                    className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 text-xs flex items-center justify-between hover:border-cyan-500/40 transition-colors"
                  >
                    <div>
                      <div className="font-bold text-white font-mono">{proxy.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">{proxy.host}:{proxy.port}</div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="text-emerald-400 font-semibold">{proxy.playersCount} players</div>
                      <div className="text-[10px] text-slate-500">{proxy.cpuPercent}% CPU</div>
                    </div>
                  </div>
                ))
              )}
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed font-mono">
              ⚡ Modern Bungee/Velocity routing with modern TLS handshake & Bedrock Geyser connector support.
            </p>
          </div>

          {/* Layer 2: Routing Hubs & Game Nodes (Paper/Purpur/Fabric) */}
          <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-indigo-300">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" />
                <span>Tier 2: Game Instance Nodes</span>
              </div>
              <span className="font-mono text-[10px] bg-indigo-950/80 border border-indigo-500/30 px-2 py-0.5 rounded text-indigo-300">
                {servers.filter(s => s.type !== 'velocity_proxy').length} Cores
              </span>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {servers.filter(s => s.type !== 'velocity_proxy').length === 0 ? (
                <div className="p-3 text-xs font-mono text-slate-500 text-center">
                  Awaiting instance heartbeat telemetry from backend.
                </div>
              ) : (
                servers.filter(s => s.type !== 'velocity_proxy').map(srv => (
                  <div 
                    key={srv.id}
                    onClick={() => {
                      setSelectedServerId(srv.id);
                      setActiveTab('console');
                    }}
                    className="rounded-lg border border-slate-800 bg-slate-900/80 p-2.5 text-xs flex items-center justify-between hover:border-indigo-500/40 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className={`h-2 w-2 rounded-full ${srv.status === 'online' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
                      <div>
                        <div className="font-bold text-white font-mono text-[11px] truncate">{srv.name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{srv.type}</div>
                      </div>
                    </div>
                    <div className="text-right font-mono shrink-0">
                      <span className={`text-[11px] font-bold ${srv.tps < 18 ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {srv.tps} TPS
                      </span>
                      <div className="text-[10px] text-slate-500">{srv.playersCount}p</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Layer 3: Data Plane (PostgreSQL + Redis + Storage) */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-emerald-300">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-emerald-400" />
                <span>Tier 3: Data Plane & Storage</span>
              </div>
              <span className="font-mono text-[10px] bg-emerald-950/80 border border-emerald-500/30 px-2 py-0.5 rounded text-emerald-300">
                HA Cluster
              </span>
            </div>

            <div className="space-y-2">
              <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-white">PostgreSQL 16 HA (Render Frankfurt)</span>
                  <span className="text-emerald-400 text-[10px]">Connected</span>
                </div>
                <div className="mt-1 text-[10px] font-mono text-slate-400">
                  Player states, Bans ledger, CoreProtect partitioned block events.
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-white">Redis 7.2 Cache (PubSub & IPC)</span>
                  <span className="text-cyan-400 text-[10px]">Online</span>
                </div>
                <div className="mt-1 text-[10px] font-mono text-slate-400">
                  Instant LuckPerms rank broadcast & cross-server chat channels.
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-white">Snapshot Volume Storage</span>
                  <span className="text-indigo-400 text-[10px]">Active Delta</span>
                </div>
                <div className="mt-1 text-[10px] font-mono text-slate-400">
                  Automated delta backups with retention management.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Host Baremetal Nodes Grid + Deep Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Node Hardware Cards */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white tracking-tight font-display">Compute Nodes & Container Hosts</h2>
            <span className="text-xs font-mono text-slate-400">{filteredNodes.length} Hosts Monitored</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredNodes.length === 0 ? (
              <div className="col-span-2 p-6 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
                No external baremetal nodes configured. Server instances running in containerized runtime.
              </div>
            ) : (
              filteredNodes.map(node => {
                const isSelected = node.id === selectedNodeId;
                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNodeId(node.id)}
                    className={`rounded-xl border p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-cyan-500/60 bg-cyan-950/20 shadow-md ring-1 ring-cyan-500/30'
                        : 'border-slate-800 bg-[#0c1017] hover:border-slate-700 hover:bg-slate-900/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
                        <span className="font-bold text-white text-xs font-mono">{node.name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                        {node.pingMs}ms
                      </span>
                    </div>

                    <div className="mt-3 text-[11px] font-mono text-slate-400 flex items-center justify-between">
                      <span>{node.region}</span>
                      <span className="text-cyan-300">{node.ip}</span>
                    </div>

                    {/* CPU Usage bar */}
                    <div className="mt-3 space-y-1">
                      <div className="flex justify-between text-[10px] font-mono text-slate-400">
                        <span>CPU Load ({node.cpuCores} Threads)</span>
                        <span className="text-white font-bold">{node.cpuUsage}%</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className={`h-full ${node.cpuUsage > 75 ? 'bg-amber-500' : 'bg-cyan-500'}`}
                          style={{ width: `${node.cpuUsage}%` }}
                        />
                      </div>
                    </div>

                    {/* RAM Usage bar */}
                    <div className="mt-2 space-y-1">
                      <div className="flex justify-between text-[10px] font-mono text-slate-400">
                        <span>RAM Allocation</span>
                        <span className="text-white font-bold">{node.ramGb} / {node.ramTotalGb} GB</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className="h-full bg-indigo-500"
                          style={{ width: `${(node.ramGb / (node.ramTotalGb || 1)) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                      <span>Plugin: {node.daemonVersion || 'umbrella-core-bridge'}</span>
                      <span className="text-slate-300 font-semibold">{node.assignedServers?.length || 0} Instances</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right 1 Col: Selected Node Inspector Drawer */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white tracking-tight font-display">Node Host Inspector</h2>
            <SlidersHorizontal className="h-4 w-4 text-cyan-400" />
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-4">
            {selectedNode ? (
              <>
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white font-mono">{selectedNode.name}</span>
                    <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
                      {selectedNode.status?.toUpperCase() || 'ONLINE'}
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-slate-400 mt-1">
                    IP: {selectedNode.ip} • Region: {selectedNode.region}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/60">
                    <div className="text-[10px] text-slate-500">Network In</div>
                    <div className="text-white font-bold mt-0.5">{selectedNode.networkInMbps} Mbps</div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/60">
                    <div className="text-[10px] text-slate-500">Network Out</div>
                    <div className="text-white font-bold mt-0.5">{selectedNode.networkOutMbps} Mbps</div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/60">
                    <div className="text-[10px] text-slate-500">Disk Used</div>
                    <div className="text-white font-bold mt-0.5">{selectedNode.diskUsageGb} GB / {selectedNode.diskTotalGb} GB</div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/60">
                    <div className="text-[10px] text-slate-500">Plugin Version</div>
                    <div className="text-emerald-400 font-bold mt-0.5">{selectedNode.daemonVersion || 'umbrella-core-bridge'}</div>
                  </div>
                </div>

                {/* Assigned Servers on this node */}
                <div>
                  <div className="text-xs font-semibold text-slate-300 mb-2">Hosted Minecraft Instances</div>
                  <div className="space-y-1.5">
                    {assignedServers.length === 0 ? (
                      <div className="text-xs text-slate-500 p-3 bg-slate-900/40 rounded-lg text-center font-mono">
                        Dedicated storage/data infrastructure node.
                      </div>
                    ) : (
                      assignedServers.map(s => (
                        <div 
                          key={s.id}
                          className="flex items-center justify-between p-2 rounded-lg border border-slate-800 bg-slate-900/40 text-xs font-mono"
                        >
                          <span className="text-white font-semibold">{s.name}</span>
                          <span className="text-cyan-400">{s.playersCount} players</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Actions for this node */}
                <div className="pt-3 border-t border-slate-800 space-y-2">
                  <button
                    onClick={() => handleDrainNode(selectedNode.id)}
                    className="w-full py-2 px-3 rounded-lg border border-amber-500/20 bg-amber-950/20 hover:bg-amber-950/40 text-amber-200 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                    <span>Drain & Migrate Players</span>
                  </button>
                  <button
                    onClick={() => handleRestartPlugin(selectedNode.id)}
                    className="w-full py-2 px-3 rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-800 text-slate-200 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <RefreshCw className="h-3.5 w-3.5 text-slate-400" />
                    <span>Reload Umbrella Plugin</span>
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-xs text-slate-500 font-mono">
                Select a node to inspect telemetry.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
