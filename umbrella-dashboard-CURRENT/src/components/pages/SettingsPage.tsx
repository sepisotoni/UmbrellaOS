import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { settings, aiConfig, SettingRecord, TaskConfigResponse } from '../../lib/api'
import { Card, Button, Input, Skeleton, ErrorCard, Tabs, Select } from '../ui'
import { Eye, EyeOff, Save, CheckCircle2, RefreshCw, Zap } from 'lucide-react'

// ── Core Connection (client-side only) ───────────────────────────────────────

function CoreConnectionSection() {
  const [url, setUrl] = useState(
    () => localStorage.getItem('umbrella_core_url_override') ?? import.meta.env.VITE_UMBRELLA_CORE_URL ?? '',
  )
  const [saved, setSaved] = useState(false)

  const save = () => {
    if (url.trim()) localStorage.setItem('umbrella_core_url_override', url.trim())
    else localStorage.removeItem('umbrella_core_url_override')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-[11px] text-amber-300">
        Client-side only — this URL override is stored in your browser and never sent to the backend.
        Leave blank to use the value from <span className="font-mono">VITE_UMBRELLA_CORE_URL</span>.
      </div>
      <div>
        <label className="text-[11px] text-slate-500 mb-1 block">FastAPI Base URL</label>
        <div className="flex gap-2">
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={import.meta.env.VITE_UMBRELLA_CORE_URL ?? 'http://localhost:8000'}
          />
          <Button variant={saved ? 'secondary' : 'primary'} onClick={save}>
            {saved
              ? <><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Saved</>
              : <><Save className="h-3.5 w-3.5" /> Save</>}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Generic backend settings editor ──────────────────────────────────────────

function BackendSettingsEditor({ keys }: { keys: string[] }) {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<SettingRecord[]>(
    token ? () => settings.list(token) : null, [token],
  )

  const [edits, setEdits] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<string | null>(null)
  const [revealed, setRevealed] = useState<Set<string>>(new Set())
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({})
  const [saveOk, setSaveOk] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (data) {
      const map: Record<string, string> = {}
      data.filter((s) => keys.includes(s.key)).forEach((s) => { map[s.key] = s.value })
      setEdits((prev) => ({ ...map, ...prev }))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  const handleSave = async (key: string) => {
    if (!token) return
    setSaving(key)
    setSaveErrors((e) => { const n = { ...e }; delete n[key]; return n })
    try {
      // POST /api/v1/settings/{key} — upsert, more forgiving than PATCH
      await settings.update(token, key, edits[key] ?? '')
      setSaveOk((s) => { const n = new Set(s); n.add(key); setTimeout(() => setSaveOk((p) => { const pp = new Set(p); pp.delete(key); return pp }), 2000); return n })
      reload()
    } catch (err) {
      setSaveErrors((e) => ({ ...e, [key]: err instanceof Error ? err.message : 'Save failed' }))
    } finally {
      setSaving(null)
    }
  }

  if (loading) return <Skeleton className="h-32 w-full" />
  if (error) return <ErrorCard message={error} onRetry={reload} />

  const displayed = (data ?? []).filter((s) => keys.includes(s.key))
  const missingKeys = keys.filter((k) => !displayed.find((s) => s.key === k))

  return (
    <div className="space-y-3">
      {[...displayed.map((s) => s.key), ...missingKeys].map((key) => {
        const s = displayed.find((x) => x.key === key)
        const isSensitive = s?.sensitive ?? false
        return (
          <div key={key}>
            <label className="text-[11px] text-slate-500 mb-1 block font-mono">{key}</label>
            <div className="flex gap-2 items-center">
              <div className="flex-1 relative">
                <Input
                  value={edits[key] ?? ''}
                  onChange={(e) => setEdits((ed) => ({ ...ed, [key]: e.target.value }))}
                  type={isSensitive && !revealed.has(key) ? 'password' : 'text'}
                  placeholder={isSensitive ? '(masked)' : key}
                />
                {isSensitive && (
                  <button
                    onClick={() => setRevealed((r) => { const n = new Set(r); n.has(key) ? n.delete(key) : n.add(key); return n })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 cursor-pointer"
                  >
                    {revealed.has(key) ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                )}
              </div>
              <Button
                variant={saveOk.has(key) ? 'secondary' : 'primary'}
                loading={saving === key}
                onClick={() => handleSave(key)}
              >
                {saveOk.has(key) ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <Save className="h-3.5 w-3.5" />}
              </Button>
            </div>
            {saveErrors[key] && <p className="text-[11px] text-red-400 mt-1">{saveErrors[key]}</p>}
          </div>
        )
      })}
    </div>
  )
}

// ── AI Configuration (uses real /api/v1/ai/config/tasks endpoints) ────────────

const VALID_PROVIDERS = ['gemini', 'anthropic', 'openai', 'deepseek', 'openrouter'] as const
type Provider = typeof VALID_PROVIDERS[number]

const TASK_LABELS: Record<string, string> = {
  player_review: 'Player Review',
  appeal_review: 'Appeal Review',
  copilot: 'Copilot Chat',
  crash_risk: 'Crash Risk',
  chat_responder: 'Chat Responder',
}

function AIConfigSection() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<TaskConfigResponse>(
    token ? () => aiConfig.getTasks(token) : null, [token],
  )
  const [saving, setSaving] = useState<string | null>(null)
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({})
  const [localConfig, setLocalConfig] = useState<TaskConfigResponse | null>(null)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; msg: string }>>({})

  useEffect(() => { if (data) setLocalConfig(data) }, [data])

  const config = localConfig ?? data

  const handleUpdate = async (task: string, primary: string, failover: string | null) => {
    if (!token) return
    setSaving(task)
    setSaveErrors((e) => { const n = { ...e }; delete n[task]; return n })
    try {
      const updated = await aiConfig.updateTask(token, { task, primary, failover })
      setLocalConfig(updated)
    } catch (err) {
      setSaveErrors((e) => ({ ...e, [task]: err instanceof Error ? err.message : 'Save failed' }))
    } finally {
      setSaving(null)
    }
  }

  const handleTest = async (provider: string) => {
    if (!token) return
    setTesting(provider)
    try {
      const result = await aiConfig.testProvider(token, { provider })
      setTestResults((r) => ({ ...r, [provider]: { ok: result.success, msg: result.message } }))
    } catch (err) {
      setTestResults((r) => ({ ...r, [provider]: { ok: false, msg: err instanceof Error ? err.message : 'Test failed' } }))
    } finally {
      setTesting(null)
    }
  }

  if (loading) return <Skeleton className="h-40 w-full" />
  if (error) return <ErrorCard message={error} onRetry={reload} />
  if (!config) return null

  const tasks = Object.entries(config) as [keyof TaskConfigResponse, { primary: string; failover: string | null }][]

  return (
    <div className="space-y-5">
      {/* Per-task model selector */}
      <div className="space-y-4">
        <p className="text-[11px] text-slate-500 uppercase tracking-wider">Per-task Model Assignments</p>
        {tasks.map(([task, assignment]) => (
          <div key={task} className="rounded-lg bg-white/[0.03] border border-white/[0.07] p-3 space-y-2">
            <p className="text-xs font-medium text-slate-200">{TASK_LABELS[task] ?? task}</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Primary</label>
                <Select
                  value={assignment.primary}
                  onChange={(e) => handleUpdate(task, e.target.value, assignment.failover)}
                  disabled={saving === task}
                  className="w-full"
                >
                  {VALID_PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
                </Select>
              </div>
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Failover</label>
                <Select
                  value={assignment.failover ?? ''}
                  onChange={(e) => handleUpdate(task, assignment.primary, e.target.value || null)}
                  disabled={saving === task}
                  className="w-full"
                >
                  <option value="">None</option>
                  {VALID_PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
                </Select>
              </div>
            </div>
            {saving === task && <p className="text-[11px] text-slate-500">Saving…</p>}
            {saveErrors[task] && <p className="text-[11px] text-red-400">{saveErrors[task]}</p>}
          </div>
        ))}
      </div>

      {/* Provider live tests */}
      <div className="space-y-2">
        <p className="text-[11px] text-slate-500 uppercase tracking-wider">Provider Live Tests</p>
        <div className="flex flex-wrap gap-2">
          {VALID_PROVIDERS.map((provider) => {
            const result = testResults[provider]
            return (
              <div key={provider} className="flex items-center gap-1.5">
                <Button
                  variant="secondary"
                  loading={testing === provider}
                  onClick={() => handleTest(provider)}
                  className="py-1 px-3"
                >
                  <Zap className="h-3 w-3" />
                  {provider}
                </Button>
                {result && (
                  <span className={`text-[10px] ${result.ok ? 'text-emerald-400' : 'text-red-400'}`}>
                    {result.ok ? '✓' : '✗'} {result.msg.slice(0, 40)}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* API Keys (from settings) */}
      <div className="space-y-2">
        <p className="text-[11px] text-slate-500 uppercase tracking-wider">API Keys</p>
        <BackendSettingsEditor keys={[
          'ai.anthropic_api_key',
          'ai.gemini_api_key',
          'ai.openai_api_key',
          'ai.openrouter_api_key',
          'ai.deepseek_api_key',
        ]} />
      </div>
    </div>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'core', label: 'Core Connection' },
  { id: 'discord', label: 'Discord' },
  { id: 'verification', label: 'Verification Messages' },
  { id: 'greeter', label: 'Greeter Messages' },
  { id: 'ai', label: 'AI Configuration' },
]

export function SettingsPage() {
  const [tab, setTab] = useState('core')

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Settings</h1>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'core' && (
        <Card><CoreConnectionSection /></Card>
      )}

      {tab === 'discord' && (
        <Card>
          <p className="text-[11px] text-slate-500 mb-3 uppercase tracking-wider">Discord Settings</p>
          <BackendSettingsEditor keys={['discord.invite_url', 'discord.guild_id']} />
        </Card>
      )}

      {tab === 'verification' && (
        <div className="space-y-3">
          <Card className="text-xs text-slate-400 space-y-1">
            <p className="font-medium text-slate-300">Template variables:</p>
            <p className="font-mono text-violet-300">$CODE &nbsp; $PLAYER &nbsp; $DISCORD_INVITE &nbsp; $SERVER &nbsp; $EXPIRES</p>
          </Card>
          <Card>
            <BackendSettingsEditor keys={[
              'verification.join_message',
              'verification.success_message',
            ]} />
          </Card>
        </div>
      )}

      {tab === 'greeter' && (
        <Card>
          <BackendSettingsEditor keys={[
            'greeter.first_join_message',
            'greeter.return_join_message',
          ]} />
        </Card>
      )}

      {tab === 'ai' && (
        <Card><AIConfigSection /></Card>
      )}
    </div>
  )
}
