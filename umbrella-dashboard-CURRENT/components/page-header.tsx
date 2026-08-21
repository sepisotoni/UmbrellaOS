export function PageHeader({ title, description, eyebrow = "UmbrellaOS / Control room", children }: { title: string; description?: string; eyebrow?: string; children?: React.ReactNode }) {
  return (
    <div className="relative flex flex-col gap-5 overflow-hidden rounded-2xl border border-border bg-card/80 px-5 py-5 shadow-[0_20px_60px_color-mix(in_oklab,var(--primary)_8%,transparent)] sm:flex-row sm:items-end sm:justify-between sm:px-6">
      <div className="pointer-events-none absolute inset-y-0 right-0 w-1/3 bg-[radial-gradient(ellipse_at_right,color-mix(in_oklab,var(--primary)_18%,transparent),transparent_70%)]" />
      <div className="relative flex flex-col gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">{eyebrow}</p>
        <h1 className="text-pretty text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{title}</h1>
        {description ? <p className="max-w-2xl text-pretty text-sm leading-6 text-muted-foreground">{description}</p> : null}
      </div>
      {children ? <div className="relative flex items-center gap-2">{children}</div> : null}
    </div>
  )
}
