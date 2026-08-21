"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useRouter } from "next/navigation";

type Action = "kick" | "warn" | "ban" | "ai-review" | null;

export function PlayerActions({
  playerUuid,
  token,
}: {
  playerUuid: string;
  token: string;
}) {
  const router = useRouter();
  const [action, setAction] = useState<Action>(null);
  const [reason, setReason] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    setResult(null);
    try {
      let path = `/api/v1/moderation/${action}`;
      const body: Record<string, string> = { player_uuid: playerUuid, reason };
      if (action === "ban" && expiresAt) body.expires_at = expiresAt;
      if (action === "ai-review") {
        path = `/api/v1/ai/review/player/${playerUuid}`;
      }

      const res = await fetch(`/api/moderation-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, body, token }),
      });

      if (!res.ok) {
        const text = await res.text();
        setResult(`Error: ${text}`);
      } else {
        setResult("Done.");
        router.refresh();
        setTimeout(() => {
          setAction(null);
          setReason("");
          setResult(null);
        }, 1500);
      }
    } catch (e) {
      setResult(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="rounded-xl border border-border bg-card/60 p-5 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-50">
          Actions
        </p>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => setAction("kick")}>
            Kick
          </Button>
          <Button variant="outline" size="sm" onClick={() => setAction("warn")}>
            Warn
          </Button>
          <Button variant="destructive" size="sm" onClick={() => setAction("ban")}>
            Ban
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setAction("ai-review")}>
            Trigger AI Review
          </Button>
        </div>
      </div>

      <Dialog open={action !== null} onOpenChange={() => setAction(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="capitalize">
              {action === "ai-review" ? "Trigger AI Review" : action}
            </DialogTitle>
          </DialogHeader>
          {action !== "ai-review" && (
            <div className="space-y-3 py-2">
              <Input
                placeholder="Reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              {action === "ban" && (
                <Input
                  type="datetime-local"
                  placeholder="Expires at (optional)"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                />
              )}
            </div>
          )}
          {result && (
            <p className="text-sm text-muted-foreground">{result}</p>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAction(null)}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={loading}>
              {loading ? "Sending…" : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
