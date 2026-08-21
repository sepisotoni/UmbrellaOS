// components/widgets/stat-pair.tsx — one of the dashboard's own trusted
// rendering components (Decision 1). Takes plain data, renders it with
// React's normal text-content escaping — a plugin's capability result can
// only ever end up as text here, never markup.
export function StatPair({
  label,
  data,
}: {
  label: string;
  data: Record<string, unknown>;
}) {
  const entries = Object.entries(data);
  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">{label}</h3>
      <dl className="flex flex-wrap gap-4">
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt className="text-xs opacity-50">{key}</dt>
            <dd className="text-lg font-semibold">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
