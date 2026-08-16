"use client";

// components/widgets/dashboard-customizer.tsx — Phase 10 step 6's one
// 'use client' leaf for custom dashboards (Decision 6: scope client
// components to genuinely interactive leaves, same as the command palette
// in step 4). Everything else about layout resolution stays server-side
// (widget-grid.tsx).
//
// Deliberately plain up/down buttons + a visibility checkbox instead of a
// drag-and-drop library: no new npm dependency whose install this sandbox
// can't verify (same call step 5 made for the topology canvas), and a
// small fixed widget count doesn't need pointer-based DnD to be usable.
import { useRouter } from "next/navigation";
import { useState } from "react";

type CustomizerEntry = {
  widgetKey: string;
  label: string;
  visible: boolean;
};

export function DashboardCustomizer({
  pageId,
  initialWidgets,
}: {
  pageId: string;
  initialWidgets: CustomizerEntry[];
}) {
  const [open, setOpen] = useState(false);
  const [widgets, setWidgets] = useState(initialWidgets);
  const [saving, setSaving] = useState(false);
  const router = useRouter();

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= widgets.length) return;
    const next = [...widgets];
    const a = next[index];
    const b = next[target];
    if (!a || !b) return;
    next[index] = b;
    next[target] = a;
    setWidgets(next);
  }

  function toggleVisible(index: number) {
    const current = widgets[index];
    if (!current) return;
    const next = [...widgets];
    next[index] = { ...current, visible: !current.visible };
    setWidgets(next);
  }

  async function save() {
    setSaving(true);
    try {
      await fetch("/api/dashboard-layout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          page_id: pageId,
          widgets: widgets.map((w) => ({ widget_key: w.widgetKey, visible: w.visible })),
        }),
      });
      setOpen(false);
      router.refresh(); // re-fetches WidgetGrid server-side with the new order
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    setSaving(true);
    try {
      await fetch(`/api/dashboard-layout?page_id=${encodeURIComponent(pageId)}`, {
        method: "DELETE",
      });
      setOpen(false);
      router.refresh();
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded border border-[var(--border)] px-3 py-1 text-xs opacity-70 hover:opacity-100"
      >
        Customize
      </button>
    );
  }

  return (
    <div className="w-full max-w-sm rounded-lg border border-[var(--border)] p-3 text-sm">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide opacity-60">
        Widget order &amp; visibility
      </p>
      <ul className="mb-3 space-y-1">
        {widgets.map((w, i) => (
          <li
            key={w.widgetKey}
            className="flex items-center justify-between gap-2 rounded px-2 py-1 hover:bg-white/5"
          >
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={w.visible}
                onChange={() => toggleVisible(i)}
              />
              <span className={w.visible ? "" : "opacity-40"}>{w.label}</span>
            </label>
            <span className="flex gap-1">
              <button
                aria-label={`Move ${w.label} up`}
                onClick={() => move(i, -1)}
                disabled={i === 0}
                className="px-1 opacity-70 hover:opacity-100 disabled:opacity-20"
              >
                ↑
              </button>
              <button
                aria-label={`Move ${w.label} down`}
                onClick={() => move(i, 1)}
                disabled={i === widgets.length - 1}
                className="px-1 opacity-70 hover:opacity-100 disabled:opacity-20"
              >
                ↓
              </button>
            </span>
          </li>
        ))}
      </ul>
      <div className="flex justify-between gap-2">
        <button
          onClick={reset}
          disabled={saving}
          className="text-xs opacity-60 hover:opacity-100"
        >
          Reset to default
        </button>
        <span className="flex gap-2">
          <button
            onClick={() => setOpen(false)}
            disabled={saving}
            className="rounded border border-[var(--border)] px-3 py-1 text-xs"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="rounded bg-[var(--accent)] px-3 py-1 text-xs text-black"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </span>
      </div>
    </div>
  );
}
