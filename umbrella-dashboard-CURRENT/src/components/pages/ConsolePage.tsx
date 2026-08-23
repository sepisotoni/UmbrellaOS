import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { dashboard, ServerRecord, openConsoleWebSocket } from '../../lib/api'
import { Card, Button, Input, Select, ErrorCard, Skeleton } from '../ui'
import { Terminal, Send, Power } from 'lucide-react'

interface LogLine {
  id: number
  text: string
  ts: number
}

let logIdCounter = 0

export function ConsolePage() {
  const { token } = useAuth()
  const [selectedServer, setSelectedServer] = useState<string>('')
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [wsError, setWsError] = useState<string | null>(null)
  const [lines, setLines] = useState<LogLine[]>([])
  const [input, setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  const { data: servers, loading: serversLoading } = useFetch<ServerRecord[]>(
    token ? () => dashboard.servers(token) : null,
    [token],
  )

  const addLine = useCallback((text: string) => {
    setLines((prev) => [...prev.slice(-500), { id: ++logIdCounter, text, ts: Date.now() }])
  }, [])

  // Scroll to bottom on new lines
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  // Disconnect on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  const connect = useCallback(() => {
    if (!token || !selectedServer) return
    wsRef.current?.close()
    setConnecting(true)
    setWsError(null)
    setLines([])

    const ws = openConsoleWebSocket(selectedServer, token)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setConnecting(false)
      addLine('[Console connected]')
    }

    ws.onmessage = (evt) => {
      const text = typeof evt.data === 'string' ? evt.data : '[binary frame]'
      addLine(text)
    }

    ws.onerror = () => {
      setWsError('WebSocket error — check that the server ID is correct and the server is online.')
      setConnecting(false)
    }

    ws.onclose = (evt) => {
      setConnected(false)
      setConnecting(false)
      addLine(`[Console disconnected — code ${evt.code}]`)
    }
  }, [token, selectedServer, addLine])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    setConnected(false)
    addLine('[Console disconnected by user]')
  }, [addLine])

  const sendCommand = useCallback(() => {
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(input.trim())
    addLine(`> ${input.trim()}`)
    setInput('')
  }, [input, addLine])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') sendCommand()
  }

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Console</h1>
        <p className="text-[11px] text-slate-500">WebSocket connects only when you open this page.</p>
      </div>

      {/* Server selector + connect */}
      <div className="flex items-center gap-3">
        {serversLoading ? (
          <Skeleton className="h-9 w-48" />
        ) : (
          <Select
            value={selectedServer}
            onChange={(e) => setSelectedServer(e.target.value)}
            disabled={connected}
          >
            <option value="">Select a server…</option>
            {(servers ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </Select>
        )}

        {!connected ? (
          <Button
            variant="primary"
            loading={connecting}
            disabled={!selectedServer}
            onClick={connect}
          >
            <Terminal className="h-3.5 w-3.5" />
            Connect
          </Button>
        ) : (
          <Button variant="danger" onClick={disconnect}>
            <Power className="h-3.5 w-3.5" />
            Disconnect
          </Button>
        )}

        {connected && (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </span>
        )}
      </div>

      {wsError && <ErrorCard message={wsError} />}

      {/* Terminal output */}
      <div className="flex-1 min-h-[400px] rounded-xl border border-white/[0.07] bg-[#050709] overflow-y-auto p-4 font-mono text-xs text-green-400">
        {lines.length === 0 && (
          <p className="text-slate-600">
            {connected ? 'Waiting for output…' : 'Connect to a server to view its console.'}
          </p>
        )}
        {lines.map((l) => (
          <div key={l.id} className="whitespace-pre-wrap leading-5 text-[11px]">
            <span className="text-slate-600 select-none mr-2">{new Date(l.ts).toTimeString().slice(0, 8)}</span>
            {l.text}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>

      {/* Command input */}
      <div className="flex items-center gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={connected ? 'Type a command and press Enter…' : 'Not connected'}
          disabled={!connected}
          className="font-mono"
        />
        <Button variant="primary" disabled={!connected || !input.trim()} onClick={sendCommand}>
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
