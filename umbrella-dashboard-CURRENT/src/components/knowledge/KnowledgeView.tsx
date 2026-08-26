import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api, KnowledgeEntry, KnowledgeVersion } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  BookOpen,
  Search,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Clock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────────────────

const CATEGORIES = ['general', 'rules', 'anticheat', 'appeals', 'server', 'verification'];

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function statusBadge(status: string) {
  if (status === 'approved')
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border bg-emerald-950/60 text-emerald-300 border-emerald-800/40 font-mono font-bold uppercase tracking-wide">
        <CheckCircle2 className="h-3 w-3" />
        Approved
      </span>
    );
  if (status === 'pending')
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border bg-amber-950/60 text-amber-300 border-amber-800/40 font-mono font-bold uppercase tracking-wide">
        <Clock className="h-3 w-3" />
        Pending
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border bg-rose-950/60 text-rose-300 border-rose-800/40 font-mono font-bold uppercase tracking-wide">
      <XCircle className="h-3 w-3" />
      Rejected
    </span>
  );
}

// ─── Create Modal ────────────────────────────────────────────────────────────

interface CreateModalProps {
  onClose: () => void;
  onCreated: (entry: KnowledgeEntry) => void;
}

const CreateModal: React.FC<CreateModalProps> = ({ onClose, onCreated }) => {
  const { addToast } = useDashboard();
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('general');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!title.trim() || !content.trim()) return;
    setSubmitting(true);
    try {
      const entry = await api.createKnowledgeEntry({ title: title.trim(), content: content.trim(), category });
      addToast({ type: 'success', message: 'Knowledge entry created.' });
      onCreated(entry);
    } catch (e: any) {
      addToast({ type: 'error', message: e.message || 'Failed to create entry.' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg mx-4 rounded-xl border border-[#1e2a5e] bg-[#060b1c] shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-indigo-400" />
            Add Knowledge Entry
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition cursor-pointer">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Title</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Brief title for this entry"
              className="w-full rounded-lg border border-[#1e2a5e] bg-[#02040a] px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Category</label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full rounded-lg border border-[#1e2a5e] bg-[#02040a] px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none cursor-pointer"
            >
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Content</label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              rows={7}
              placeholder="Full knowledge base content…"
              className="w-full rounded-lg border border-[#1e2a5e] bg-[#02040a] px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none resize-none font-mono"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded-lg border border-[#1e2a5e] hover:border-slate-500 transition cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !title.trim() || !content.trim()}
            className="px-4 py-1.5 text-xs font-bold text-white rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition cursor-pointer"
          >
            {submitting ? 'Creating…' : 'Create Entry'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Detail Panel ────────────────────────────────────────────────────────────

interface DetailPanelProps {
  entry: KnowledgeEntry;
  onUpdated: (entry: KnowledgeEntry) => void;
  onDeleted: (id: string) => void;
}

const DetailPanel: React.FC<DetailPanelProps> = ({ entry, onUpdated, onDeleted }) => {
  const { addToast } = useDashboard();
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(entry.content);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [versions, setVersions] = useState<KnowledgeVersion[]>([]);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [reviewing, setReviewing] = useState<'approve' | 'reject' | null>(null);

  // Reset edit state when entry changes
  useEffect(() => {
    setEditing(false);
    setEditContent(entry.content);
    setConfirmDelete(false);
    setVersionsOpen(false);
    setVersions([]);
  }, [entry.id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.updateKnowledgeEntry(entry.id, editContent);
      addToast({ type: 'success', message: 'Entry updated.' });
      setEditing(false);
      onUpdated(updated);
    } catch (e: any) {
      addToast({ type: 'error', message: e.message || 'Failed to update.' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.deleteKnowledgeEntry(entry.id);
      addToast({ type: 'success', message: 'Entry deleted.' });
      onDeleted(entry.id);
    } catch (e: any) {
      addToast({ type: 'error', message: e.message || 'Failed to delete.' });
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  const loadVersions = async () => {
    if (versionsOpen) { setVersionsOpen(false); return; }
    setVersionsLoading(true);
    try {
      const data = await api.getKnowledgeEntryDetail(entry.id);
      setVersions(data.versions);
    } catch {
      // ignore
    } finally {
      setVersionsLoading(false);
      setVersionsOpen(true);
    }
  };

  const handleReview = async (action: 'approve' | 'reject') => {
    setReviewing(action);
    try {
      const updated = action === 'approve'
        ? await api.approveKnowledge(entry.id)
        : await api.rejectKnowledge(entry.id);
      addToast({ type: 'success', message: `Entry ${action}d.` });
      onUpdated(updated);
    } catch (e: any) {
      addToast({ type: 'error', message: e.message || `Failed to ${action}.` });
    } finally {
      setReviewing(null);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-none p-4 border-b border-[#141d3d] space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs px-2 py-0.5 rounded border border-indigo-700/50 bg-indigo-950/50 text-indigo-300 font-mono">
              {entry.channel_name}
            </span>
            {statusBadge(entry.review_status)}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {!editing && (
              <button
                onClick={() => { setEditing(true); setEditContent(entry.content); }}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-[#1e2a5e] text-slate-400 hover:text-indigo-300 hover:border-indigo-700/50 transition text-xs cursor-pointer"
              >
                <Edit2 className="h-3 w-3" /> Edit
              </button>
            )}
            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-[#1e2a5e] text-slate-400 hover:text-rose-400 hover:border-rose-700/50 transition text-xs cursor-pointer"
              >
                <Trash2 className="h-3 w-3" /> Delete
              </button>
            ) : (
              <div className="flex items-center gap-1">
                <span className="text-xs text-rose-400">Sure?</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-2 py-1 text-xs font-bold rounded-lg bg-rose-700 hover:bg-rose-600 text-white disabled:opacity-50 cursor-pointer"
                >
                  {deleting ? '…' : 'Yes'}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-2 py-1 text-xs rounded-lg border border-[#1e2a5e] text-slate-400 hover:text-white cursor-pointer"
                >
                  No
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span>by <span className="text-slate-300">{entry.author_name}</span></span>
          <span>{relativeTime(entry.created_at)}</span>
        </div>

        {/* Pending review actions */}
        {entry.review_status === 'pending' && (
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs text-amber-400">Awaiting review:</span>
            <button
              onClick={() => handleReview('approve')}
              disabled={!!reviewing}
              className="inline-flex items-center gap-1 px-3 py-1 text-xs font-bold rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white disabled:opacity-50 cursor-pointer"
            >
              <Check className="h-3 w-3" />
              {reviewing === 'approve' ? 'Approving…' : 'Approve'}
            </button>
            <button
              onClick={() => handleReview('reject')}
              disabled={!!reviewing}
              className="inline-flex items-center gap-1 px-3 py-1 text-xs font-bold rounded-lg bg-rose-700 hover:bg-rose-600 text-white disabled:opacity-50 cursor-pointer"
            >
              <X className="h-3 w-3" />
              {reviewing === 'reject' ? 'Rejecting…' : 'Reject'}
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {editing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={e => setEditContent(e.target.value)}
              rows={14}
              className="w-full rounded-lg border border-indigo-600/50 bg-[#02040a] px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-400 focus:outline-none resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 cursor-pointer"
              >
                <Check className="h-3 w-3" />
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={() => { setEditing(false); setEditContent(entry.content); }}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-[#1e2a5e] text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="h-3 w-3" /> Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-[#141d3d] bg-[#02040a] p-3 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
            {entry.content}
          </div>
        )}

        {/* Version history */}
        <div className="rounded-lg border border-[#141d3d] bg-[#060b1c] overflow-hidden">
          <button
            onClick={loadVersions}
            className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-400 hover:text-white transition cursor-pointer"
          >
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              Version History
            </span>
            {versionsLoading ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : versionsOpen ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
          {versionsOpen && (
            <div className="border-t border-[#141d3d] divide-y divide-[#141d3d]">
              {versions.length === 0 ? (
                <p className="px-3 py-2 text-xs text-slate-500 italic">No prior versions.</p>
              ) : (
                versions.map(v => (
                  <div key={v.version_number} className="px-3 py-2 space-y-1">
                    <div className="flex items-center gap-2 text-[11px] text-slate-500">
                      <span className="text-indigo-400 font-mono font-bold">v{v.version_number}</span>
                      <span>{relativeTime(v.created_at)}</span>
                      {v.edited_by && <span>by {v.edited_by}</span>}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono whitespace-pre-wrap line-clamp-3">
                      {v.content}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Main View ───────────────────────────────────────────────────────────────

type TabFilter = 'all' | 'approved' | 'pending' | 'rejected';

export const KnowledgeView: React.FC = () => {
  const { addToast } = useDashboard();
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<TabFilter>('all');
  const [selected, setSelected] = useState<KnowledgeEntry | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadEntries = useCallback(async (q: string, t: TabFilter) => {
    setLoading(true);
    setError(null);
    try {
      const status = t === 'all' ? undefined : t;
      const data = await api.getKnowledgeEntries({ query: q, limit: 50, status });
      setEntries(data.entries);

      // Always track pending count for badge
      if (t !== 'pending') {
        const pending = await api.getPendingKnowledge();
        setPendingCount(pending.entries.length);
      } else {
        setPendingCount(data.entries.length);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load knowledge entries.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEntries(query, tab);
  }, [tab]);

  const handleQueryChange = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadEntries(val, tab), 300);
  };

  const handleCreated = (entry: KnowledgeEntry) => {
    setEntries(prev => [entry, ...prev]);
    setSelected(entry);
    setShowCreate(false);
  };

  const handleUpdated = (updated: KnowledgeEntry) => {
    setEntries(prev => prev.map(e => (e.id === updated.id ? updated : e)));
    setSelected(updated);
    if (updated.review_status !== 'pending') {
      setPendingCount(c => Math.max(0, c - 1));
    }
  };

  const handleDeleted = (id: string) => {
    setEntries(prev => prev.filter(e => e.id !== id));
    setSelected(null);
  };

  const tabs: { key: TabFilter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'approved', label: 'Approved' },
    { key: 'pending', label: 'Pending' },
    { key: 'rejected', label: 'Rejected' },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden space-y-4">
      <DisconnectedBanner />

      {/* Header */}
      <div className="flex-none flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-400" />
            Knowledge Base
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Staff-curated reference entries and pending correction reviews.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-indigo-600/50 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition cursor-pointer"
        >
          <Plus className="h-3.5 w-3.5" /> Add Entry
        </button>
      </div>

      {/* Two-panel layout */}
      <div className="flex-1 min-h-0 flex gap-4 overflow-hidden">
        {/* Left sidebar — entry list */}
        <div className="w-72 shrink-0 flex flex-col rounded-xl border border-[#141d3d] bg-[#060b1c] overflow-hidden">
          {/* Search */}
          <div className="flex-none p-3 border-b border-[#141d3d]">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
              <input
                value={query}
                onChange={e => handleQueryChange(e.target.value)}
                placeholder="Search entries…"
                className="w-full rounded-lg border border-[#1e2a5e] bg-[#02040a] pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Tab filter */}
          <div className="flex-none flex border-b border-[#141d3d]">
            {tabs.map(t => (
              <button
                key={t.key}
                onClick={() => { setTab(t.key); setSelected(null); }}
                className={`flex-1 py-1.5 text-[11px] font-medium relative transition cursor-pointer ${
                  tab === t.key
                    ? 'text-indigo-300 border-b-2 border-indigo-500'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {t.label}
                {t.key === 'pending' && pendingCount > 0 && (
                  <span className="ml-1 text-[9px] px-1 py-0.5 rounded-full bg-amber-600 text-white font-bold">
                    {pendingCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Entry list */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="space-y-2 p-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-14 rounded-lg bg-[#0d1127] animate-pulse" />
                ))}
              </div>
            ) : error ? (
              <div className="p-4 text-center space-y-2">
                <AlertCircle className="h-6 w-6 text-rose-400 mx-auto" />
                <p className="text-xs text-rose-400">{error}</p>
                <button
                  onClick={() => loadEntries(query, tab)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
                >
                  Retry
                </button>
              </div>
            ) : entries.length === 0 ? (
              <div className="p-6 text-center space-y-3">
                <BookOpen className="h-8 w-8 text-slate-600 mx-auto" />
                <p className="text-xs text-slate-500">
                  No knowledge entries yet. Add the first one with the button above.
                </p>
              </div>
            ) : (
              entries.map(entry => (
                <button
                  key={entry.id}
                  onClick={() => setSelected(entry)}
                  className={`w-full text-left px-3 py-2.5 border-b border-[#0d1127] hover:bg-[#0d1127] transition cursor-pointer ${
                    selected?.id === entry.id ? 'bg-[#0d1127] border-l-2 border-l-indigo-500' : ''
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded border border-indigo-800/40 bg-indigo-950/40 text-indigo-400 font-mono">
                      {entry.channel_name}
                    </span>
                    {entry.review_status !== 'approved' && statusBadge(entry.review_status)}
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                    {entry.content.slice(0, 80)}{entry.content.length > 80 ? '…' : ''}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    {entry.author_name} · {relativeTime(entry.created_at)}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right panel — detail */}
        <div className="flex-1 min-w-0 rounded-xl border border-[#141d3d] bg-[#060b1c] overflow-hidden">
          {selected ? (
            <DetailPanel
              key={selected.id}
              entry={selected}
              onUpdated={handleUpdated}
              onDeleted={handleDeleted}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
              <BookOpen className="h-10 w-10 text-slate-700" />
              <p className="text-sm text-slate-500">Select an entry from the list to view details.</p>
            </div>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  );
};
