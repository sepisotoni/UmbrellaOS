"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { AppealSchema } from "@/lib/types";

const STATUS_VARIANTS: Record<string, "outline" | "secondary" | "destructive"> =
  {
    PENDING: "outline",
    ACCEPTED: "secondary",
    REJECTED: "destructive",
  };

function formatDate(d: string) {
  return new Date(d).toLocaleDateString();
}

export function AppealsTable({
  appeals,
  token,
  canManage,
}: {
  appeals: AppealSchema[];
  token: string;
  canManage: boolean;
}) {
  const router = useRouter();
  const [selected, setSelected] = useState<AppealSchema | null>(null);
  const [decision, setDecision] = useState<"ACCEPTED" | "REJECTED" | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState<string | null>(null);

  async function submitDecision() {
    if (!selected || !decision) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/appeal-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: selected.id,
          status: decision,
          staff_notes: notes,
          token,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setSelected(null);
      setNotes("");
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function triggerAiReview(id: string) {
    setAiLoading(id);
    try {
      const res = await fetch(`/api/moderation-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: `/api/v1/ai/review/appeal/${id}`,
          body: {},
          token,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "AI review failed");
    } finally {
      setAiLoading(null);
    }
  }

  return (
    <>
      <div className="rounded-xl border border-border bg-card/60">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Player</TableHead>
              <TableHead>Punishment</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Submitted</TableHead>
              <TableHead>Status</TableHead>
              {canManage && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {appeals.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={canManage ? 6 : 5}
                  className="text-center opacity-50"
                >
                  No appeals.
                </TableCell>
              </TableRow>
            ) : (
              appeals.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-mono text-xs">
                    {a.player_username ?? a.player_uuid.slice(0, 8)}
                  </TableCell>
                  <TableCell className="font-mono text-xs opacity-60">
                    {a.punishment_id?.slice(0, 8) ?? "—"}
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate text-sm opacity-70">
                    {a.reason}
                  </TableCell>
                  <TableCell className="text-xs opacity-60">
                    {formatDate(a.submitted_at)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[a.status] ?? "outline"}>
                      {a.status}
                    </Badge>
                  </TableCell>
                  {canManage && (
                    <TableCell>
                      <div className="flex gap-2">
                        {a.status === "PENDING" && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelected(a);
                                setDecision("ACCEPTED");
                              }}
                            >
                              Accept
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelected(a);
                                setDecision("REJECTED");
                              }}
                            >
                              Reject
                            </Button>
                          </>
                        )}
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={aiLoading === a.id}
                          onClick={() => triggerAiReview(a.id)}
                        >
                          {aiLoading === a.id ? "…" : "AI Review"}
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

      <Dialog open={selected !== null} onOpenChange={() => setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {decision === "ACCEPTED" ? "Accept" : "Reject"} Appeal
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Input
              placeholder="Staff notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setSelected(null)}>
              Cancel
            </Button>
            <Button onClick={submitDecision} disabled={loading}>
              {loading ? "Submitting…" : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
