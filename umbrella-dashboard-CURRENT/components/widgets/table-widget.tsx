// components/widgets/table-widget.tsx — trusted renderer for the "table"
// shape (Phase 10, Tier 3 only — Tier 1 dashboard/sidebar slots can't
// declare this shape at the manifest level, see
// services/plugins/manifest.py's _ALLOWED_PAGE_RENDER_AS vs
// _ALLOWED_RENDER_AS). Same trust boundary as every other widget
// component: plugin data only ever flows into plain text cells via React's
// normal escaping, never markup, and columns come from the data's own keys
// — never a plugin-supplied column/header list, which would be a second
// path for a plugin to influence what's rendered beyond its own values.
function cellText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export function TableWidget({ label, data }: { label: string; data: unknown[] }) {
  const rows = data.filter(
    (row): row is Record<string, unknown> => row !== null && typeof row === "object" && !Array.isArray(row)
  );

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] p-4">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">{label}</h3>
        <p className="text-sm opacity-60">No rows.</p>
      </div>
    );
  }

  // Columns are the union of every row's keys, in first-seen order — a
  // later row with an extra key doesn't get silently dropped, and a row
  // missing a key just renders "—" for that cell (handled below).
  const columns: string[] = [];
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!columns.includes(key)) columns.push(key);
    }
  }

  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">{label}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-xs uppercase opacity-50">
              {columns.map((col) => (
                <th key={col} className="px-2 py-1.5 font-medium">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-[var(--border)]/50 last:border-0">
                {columns.map((col) => (
                  <td key={col} className="px-2 py-1.5 opacity-80">
                    {cellText(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
