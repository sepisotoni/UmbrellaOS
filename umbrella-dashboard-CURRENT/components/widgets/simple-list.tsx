// components/widgets/simple-list.tsx — trusted renderer for array-shaped
// widget data. Each entry is coerced to a plain string for display; a
// plugin cannot get anything other than text content rendered here.
function itemLabel(item: unknown): string {
  if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") {
    return String(item);
  }
  if (item && typeof item === "object") {
    const obj = item as Record<string, unknown>;
    if (typeof obj.label === "string") return obj.label;
    if (typeof obj.name === "string") return obj.name;
  }
  return JSON.stringify(item);
}

export function SimpleList({ label, data }: { label: string; data: unknown[] }) {
  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">{label}</h3>
      <ul className="space-y-1 text-sm">
        {data.map((item, i) => (
          <li key={i} className="opacity-80">
            {itemLabel(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}
