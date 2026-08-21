// components/widgets/status-badge.tsx — trusted renderer for the
// "object with a lone status string" shape.
const STATUS_COLOR: Record<string, string> = {
  online: "bg-emerald-500/20 text-emerald-400",
  offline: "bg-red-500/20 text-red-400",
  degraded: "bg-amber-500/20 text-amber-400",
  unknown: "bg-white/10 text-white/70",
};

export function StatusBadge({
  label,
  data,
}: {
  label: string;
  data: Record<string, unknown>;
}) {
  const status = String(data.status ?? "unknown").toLowerCase();
  const color = STATUS_COLOR[status] ?? STATUS_COLOR.unknown;
  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">{label}</h3>
      <span className={`inline-block rounded px-2 py-1 text-xs font-medium ${color}`}>
        {status}
      </span>
    </div>
  );
}
