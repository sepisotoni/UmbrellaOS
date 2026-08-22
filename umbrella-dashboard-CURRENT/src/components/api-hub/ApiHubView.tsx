import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import api from '../../lib/api';
import { WebhookSubscription, ApiKeyRecord } from '../../types/dashboard';
import { api } from '../../lib/api';
import {
  Webhook,
  Key,
  Code2,
  Send,
  Plus,
  Trash2,
  CheckCircle2,
  ExternalLink,
  Shield,
  Play,
  Copy,
  Lock,
  AlertTriangle,
  RefreshCw,
  Globe
} from 'lucide-react';

interface ApiHubViewProps {
  onOpenCreateApiKeyModal: () => void;
}

export const ApiHubView: React.FC<ApiHubViewProps> = ({ onOpenCreateApiKeyModal }) => {
  const {
    webhooks,
    apiKeys,
    testWebhook,
    revokeApiKey,
    backendBaseUrl,
    addToast
  } = useDashboard();

  const [deletingWebhookId, setDeletingWebhookId] = useState<string | null>(null);

  const handleDeleteWebhook = async (id: string, name: string) => {
    setDeletingWebhookId(id);
    try {
      await api.deleteWebhook(id);
      addToast('success', 'Webhook Deleted', `Webhook "${name}" removed.`);
      // Context will re-fetch on next render cycle; force by triggering a re-fetch if available
    } catch (err: any) {
      addToast('error', 'Delete Failed', err?.message || `Could not delete webhook "${name}".`);
    } finally {
      setDeletingWebhookId(null);
    }
  };

  type Tab = 'endpoints' | 'webhooks' | 'apikeys';
  const [activeTab, setActiveTab] = useState<Tab>('endpoints');
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>('GET /api/v1/dashboard/servers');
  const [apiResponse, setApiResponse] = useState<string>('// Select an endpoint and click "Send Request" to test against Render Frankfurt.');
  const [isTesting, setIsTesting] = useState(false);

  const endpoints = [
    { method: 'GET', path: '/api/v1/dashboard/servers', desc: 'List all online servers, TPS, player counts & hardware usage' },
    { method: 'GET', path: '/api/v1/dashboard/plugins', desc: 'Query UmbrellaOS Core & GrimAC connected heartbeat status' },
    { method: 'GET', path: '/api/v1/punishments', desc: 'Query ban, mute, kick, and warning records from PostgreSQL' },
    { method: 'GET', path: '/api/v1/appeals', desc: 'Fetch pending ban appeals with AI sentiment scoring' },
    { method: 'GET', path: '/api/v1/alts/flagged', desc: 'Stream flagged alt account clusters and subnet bursts' },
    { method: 'GET', path: '/api/v1/logs?limit=10', desc: 'Query centralized cluster event logs' },
    { method: 'GET', path: '/health', desc: 'Health check probe for database, redis, and daemon connectivity' }
  ];

  const handleExecuteApiTest = async () => {
    setIsTesting(true);
    
    try {
      if (selectedEndpoint.includes('/dashboard/servers')) {
        const data = await api.getServers();
        setApiResponse(JSON.stringify(data, null, 2));
      } else if (selectedEndpoint.includes('/dashboard/plugins')) {
        const data = await api.getConnectedPlugins();
        setApiResponse(JSON.stringify(data, null, 2));
      } else if (selectedEndpoint.includes('/punishments')) {
        const data = await api.getPunishments({ limit: 10 });
        setApiResponse(JSON.stringify(data, null, 2));
      } else if (selectedEndpoint.includes('/appeals')) {
        const data = await api.getAppeals();
        setApiResponse(JSON.stringify(data, null, 2));
      } else if (selectedEndpoint.includes('/alts/flagged')) {
        const data = await api.getFlaggedAlts();
        setApiResponse(JSON.stringify(data, null, 2));
      } else if (selectedEndpoint.includes('/logs')) {
        const data = await api.getLogs({ limit: 10 });
        setApiResponse(JSON.stringify(data, null, 2));
      } else if (selectedEndpoint.includes('/health')) {
        const data = await api.checkHealth();
        setApiResponse(JSON.stringify(data, null, 2));
      } else {
        setApiResponse(JSON.stringify({ status: 200, message: 'Endpoint queried successfully' }, null, 2));
      }
      addToast('success', 'HTTP 200 OK', `Executed ${selectedEndpoint} against ${backendBaseUrl}`);
    } catch (e: any) {
      setApiResponse(JSON.stringify({
        status: e.status || 500,
        error: e.message || 'Request failed',
        data: e.data || null,
        hint: 'If service is asleep on Render, wait ~20s for container spin-up.'
      }, null, 2));
      addToast('warning', 'API Error', e.message || 'Request failed');
    } finally {
      setIsTesting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    addToast('info', 'Copied to Clipboard', text);
  };

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Webhook className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight font-display">
                Developer API Hub & REST Explorer
              </h1>
              <p className="text-xs text-slate-400">
                Interactive OpenAPI 3.1 REST tester, signed webhook subscriptions, and scoped token management
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenCreateApiKeyModal}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors shadow-sm cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Generate Scoped Key</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('endpoints')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'endpoints'
              ? 'bg-slate-800 text-cyan-400 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Code2 className="h-3.5 w-3.5" />
          <span>REST API Explorer</span>
        </button>
        <button
          onClick={() => setActiveTab('webhooks')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'webhooks'
              ? 'bg-slate-800 text-cyan-400 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Webhook className="h-3.5 w-3.5" />
          <span>Webhooks Subscriptions ({webhooks.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('apikeys')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'apikeys'
              ? 'bg-slate-800 text-cyan-400 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Key className="h-3.5 w-3.5" />
          <span>API Keys & RBAC ({apiKeys.length})</span>
        </button>
      </div>

      {/* TAB 1: REST API EXPLORER */}
      {activeTab === 'endpoints' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Endpoint List */}
          <div className="lg:col-span-5 space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">Available Endpoints</span>
            <div className="space-y-1.5">
              {endpoints.map((ep) => {
                const isSelected = selectedEndpoint === `${ep.method} ${ep.path}`;
                return (
                  <button
                    key={`${ep.method}-${ep.path}`}
                    onClick={() => setSelectedEndpoint(`${ep.method} ${ep.path}`)}
                    className={`w-full p-3 rounded-lg border text-left transition-all flex flex-col gap-1 cursor-pointer ${
                      isSelected
                        ? 'border-cyan-500/50 bg-cyan-950/30 shadow-sm'
                        : 'border-slate-800/80 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/80'
                    }`}
                  >
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        ep.method === 'GET' ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/30' :
                        'bg-cyan-950 text-cyan-300 border border-cyan-500/30'
                      }`}>
                        {ep.method}
                      </span>
                      <span className="text-slate-200 font-semibold">{ep.path}</span>
                    </div>
                    <span className="text-[11px] text-slate-400">{ep.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Interactive Request & Response Box */}
          <div className="lg:col-span-7 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">Live Request Sandbox</span>
              <button
                onClick={handleExecuteApiTest}
                disabled={isTesting}
                className="flex items-center gap-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors cursor-pointer"
              >
                {isTesting ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                <span>Send Request</span>
              </button>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#07090e] p-3 space-y-3">
              <div className="flex items-center gap-2 p-2 rounded bg-slate-900 border border-slate-800 font-mono text-xs text-slate-300">
                <Globe className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                <span className="text-slate-500">{backendBaseUrl}</span>
                <span className="font-bold text-white">{selectedEndpoint}</span>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span>Response JSON Output</span>
                  <button
                    onClick={() => copyToClipboard(apiResponse)}
                    className="flex items-center gap-1 text-slate-400 hover:text-white cursor-pointer"
                  >
                    <Copy className="h-3 w-3" />
                    <span>Copy</span>
                  </button>
                </div>
                <pre className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-cyan-300 overflow-x-auto max-h-[380px] leading-relaxed">
                  {apiResponse}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: WEBHOOK SUBSCRIPTIONS */}
      {activeTab === 'webhooks' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {webhooks.map((wh) => (
              <div key={wh.id} className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white">{wh.name}</h3>
                    <p className="font-mono text-[11px] text-slate-400 mt-0.5 truncate">{wh.url}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                    wh.enabled ? 'bg-emerald-950 text-emerald-300 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {wh.enabled ? 'Active' : 'Paused'}
                  </span>
                </div>

                <div className="flex flex-wrap gap-1">
                  {wh.events.map(ev => (
                    <span key={ev} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono text-[10px] text-cyan-300">
                      {ev}
                    </span>
                  ))}
                </div>

                <div className="flex items-center justify-between border-t border-slate-800 pt-3 text-xs">
                  <span className="text-slate-400 font-mono">24h Deliveries: <strong className="text-white">{wh.deliveries24h}</strong></span>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => testWebhook(wh.id)}
                      className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-semibold cursor-pointer"
                    >
                      <Send className="h-3 w-3" />
                      <span>Test Ping</span>
                    </button>
                    <button
                      onClick={() => handleDeleteWebhook(wh.id, wh.name)}
                      disabled={deletingWebhookId === wh.id}
                      className="flex items-center gap-1 text-slate-500 hover:text-rose-400 transition-colors disabled:opacity-50"
                      title="Delete webhook"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: API KEYS */}
      {activeTab === 'apikeys' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-[#0d1117] overflow-hidden">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-slate-800 bg-slate-900/60 text-[11px] text-slate-400 uppercase">
                <tr>
                  <th className="p-3">Key Name</th>
                  <th className="p-3">Prefix</th>
                  <th className="p-3">Scopes</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {apiKeys.map(key => (
                  <tr key={key.id} className="hover:bg-slate-900/30 transition-colors">
                    <td className="p-3 font-semibold text-white">{key.name}</td>
                    <td className="p-3 text-cyan-300">{key.prefix}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1">
                        {key.scopes.map(s => (
                          <span key={s} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        key.status === 'ACTIVE' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950 text-rose-400 border border-rose-500/30'
                      }`}>
                        {key.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      {key.status === 'ACTIVE' && (
                        <button
                          onClick={() => revokeApiKey(key.id)}
                          className="p-1 rounded text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
                          title="Revoke Key"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
