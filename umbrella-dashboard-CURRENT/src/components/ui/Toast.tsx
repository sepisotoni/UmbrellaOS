import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { CheckCircle2, AlertTriangle, Info, ShieldAlert, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'grim'

interface Toast {
  id: string
  type: ToastType
  title: string
  message: string
}

interface ToastContextValue {
  addToast: (type: ToastType, title: string, message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TOAST_STYLES: Record<ToastType, { border: string; bg: string; text: string; iconColor: string }> = {
  success: {
    border: 'border-emerald-500/40',
    bg: 'bg-[#0b1812]/95',
    text: 'text-emerald-300',
    iconColor: 'text-emerald-400',
  },
  error: {
    border: 'border-rose-500/40',
    bg: 'bg-[#180b0f]/95',
    text: 'text-rose-300',
    iconColor: 'text-rose-400',
  },
  warning: {
    border: 'border-amber-500/40',
    bg: 'bg-[#18130b]/95',
    text: 'text-amber-300',
    iconColor: 'text-amber-400',
  },
  info: {
    border: 'border-purple-500/40',
    bg: 'bg-[#0b1318]/95',
    text: 'text-purple-300',
    iconColor: 'text-purple-400',
  },
  grim: {
    border: 'border-fuchsia-500/40',
    bg: 'bg-fuchsia-950/95',
    text: 'text-fuchsia-300',
    iconColor: 'text-fuchsia-400',
  },
}

const TOAST_ICONS: Record<ToastType, React.ComponentType<{ className?: string }>> = {
  success: CheckCircle2,
  error: AlertTriangle,
  warning: AlertTriangle,
  info: Info,
  grim: ShieldAlert,
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const styles = TOAST_STYLES[toast.type]
  const Icon = TOAST_ICONS[toast.type]

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 5000)
    return () => clearTimeout(timer)
  }, [toast.id, onDismiss])

  return (
    <div
      className={`relative flex items-start gap-3 rounded-xl border p-4 shadow-xl backdrop-blur-md font-mono text-xs w-80 ${styles.border} ${styles.bg}`}
    >
      <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${styles.iconColor}`} />
      <div className="flex-1 min-w-0 pr-4">
        <p className="font-bold text-white text-xs">{toast.title}</p>
        <p className={`text-[11px] font-sans mt-0.5 ${styles.text}`}>{toast.message}</p>
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="absolute top-3 right-3 text-slate-500 hover:text-slate-300 transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((type: ToastType, title: string, message: string) => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [{ id, type, title, message }, ...prev])
  }, [])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-[9999]">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
