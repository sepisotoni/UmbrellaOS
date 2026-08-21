"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AITask, AIConfigResponse } from "@/lib/types";

function formatDate(d: string) {
  return new Date(d).toLocaleDateString();
}

function ConfidenceBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="opacity-40">—</span>;
  const pct = Math.round(value * 100);
  const variant =
    pct >= 80 ? "destructive" : pct >= 50 ? "secondary" : "outline";
  return <Badge variant={variant}>{pct}%</Badge>;
}

export function AITasksList({
  tasks,
  configPending,
  token,
  canAction,
  canManageConfig,
}: {
  tasks: AITask[];
  configPending: AIConfigResponse[];
  token: string;
  canAction: boolean;
  canManageConfig: boolean;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function act(id: string, action: "approve" | "deny") {
    setLoading(`${id}-${action}`);
    try {
      const res = await fetch(`/api/ai-task-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, action, token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoading(null);
    }
  }

  async function actConfig(
    id: string,
    action: "approve" | "reject"
  ) {
    setLoading(`config-${id}-${action}`);
    try {
      const res = await fetch(`/api/ai-config-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, action, token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-card/60">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-sm font-medium">AI Review Queue</p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Recommendation</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Date</TableHead>
              {canAction && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={canAction ? 6 : 5}
                  className="text-center opacity-50"
                >
                  No pending AI tasks.
                </TableCell>
              </TableRow>
            ) : (
              tasks.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <Badge variant="outline">{t.type}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs opacity-70">
                    {t.target}
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate text-sm opacity-70">
                    {t.recommendation ?? "—"}
                  </TableCell>
                  <TableCell>
                    <ConfidenceBadge value={t.confidence} />
                  </TableCell>
                  <TableCell className="text-xs opacity-60">
                    {formatDate(t.created_at)}
                  </TableCell>
                  {canAction && (
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={!!loading}
                          onClick={() => act(t.id, "approve")}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={!!loading}
                          onClick={() => act(t.id, "deny")}
                        >
                          Deny
                        </Button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {canManageConfig && (
        <div className="rounded-xl border border-border bg-card/60">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-sm font-medium">Pending AI Config Requests</p>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Request</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {configPending.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center opacity-50">
                    No pending config requests.
                  </TableCell>
                </TableRow>
              ) : (
                configPending.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="max-w-[300px] truncate text-sm opacity-70">
                      {c.request}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{c.status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs opacity-60">
                      {formatDate(c.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={!!loading}
                          onClick={() => actConfig(c.id, "approve")}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={!!loading}
                          onClick={() => actConfig(c.id, "reject")}
                        >
                          Reject
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
