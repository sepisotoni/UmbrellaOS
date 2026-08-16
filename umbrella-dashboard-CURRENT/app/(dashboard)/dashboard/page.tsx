import { WidgetGrid } from "@/components/widgets/widget-grid";

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Dashboard</h1>
      <WidgetGrid />
    </div>
  );
}
