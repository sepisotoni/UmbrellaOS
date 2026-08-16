// components/widgets/plugin-sandbox-limits.tsx — Phase 8 completion, Task
// D: the sandbox visualizer's "what's actually enforced" panel. Thin
// wrapper around StatPair (components/widgets/stat-pair.tsx) rather than
// a bespoke layout — this is exactly the "label -> plain values" shape
// StatPair already exists for, no reason to duplicate it.
import { StatPair } from "./stat-pair";
import type { PluginSandboxLimits } from "@/lib/types";

function formatBytes(value: number): string {
  return `${(value / (1024 * 1024)).toFixed(0)} MB`;
}

export function PluginSandboxLimitsPanel({ limits }: { limits: PluginSandboxLimits }) {
  return (
    <StatPair
      label="Configured sandbox limits"
      data={{
        "CPU time": `${limits.cpu_seconds}s`,
        "Memory": formatBytes(limits.memory_bytes),
        "Wall timeout": `${limits.wall_timeout_seconds}s`,
      }}
    />
  );
}
