import { WidgetGrid } from "@/components/widgets/widget-grid";

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5 shadow-[0_20px_60px_color-mix(in_oklab,var(--primary)_8%,transparent)]"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">UmbrellaOS / Control room</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Network overview</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">A live command center for your Minecraft network, plugins, and infrastructure.</p></div>
      <WidgetGrid />
    </div>
  );
}
