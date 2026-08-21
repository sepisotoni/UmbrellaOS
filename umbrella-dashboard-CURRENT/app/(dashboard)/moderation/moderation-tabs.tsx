"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { PunishmentSchema, PunishmentType } from "@/lib/types";

const PUNISHMENT_TYPES: PunishmentType[] = [
  "BAN",
  "TEMP_BAN",
  "KICK",
  "WARN",
  "MUTE",
];

const SEVERITY_VARIANTS: Record<
  PunishmentType,
  "destructive" | "outline" | "secondary"
> = {
  BAN: "destructive",
  TEMP_BAN: "destructive",
  KICK: "secondary",
  WARN: "outline",
  MUTE: "outline",
};

function formatDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString();
}

export function ModerationTabs({
  punishments,
  token,
  canCreate,
  canRevoke,
}: {
  punishments: PunishmentSchema[];
  token: string;
  canCreate: boolean;
  canRevoke: boolean;
}) {
  const router = useRouter();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [playerUuid, setPlayerUuid] = useState("");
  const [type, setType] = useState<PunishmentType>("WARN");
  const [reason, setReason] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const activeBans = punishments.filter(
    (p) => (p.type === "BAN" || p.type === "TEMP_BAN") && !p.revoked
  );

  async function revoke(id: string) {
    try {
      const res = await fetch(`/api/punishment-revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Revoke failed");
    }
  }

  async function submitPunishment() {
    setSubmitting(true);
    setFormError(null);
    try {
      const body: Record<string, string> = {
        player_uuid: playerUuid,
        type,
        reason,
      };
      if (expiresAt) body.expires_at = expiresAt;

      const res = await fetch(`/api/punishment-create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body, token }),
      });
      if (!res.ok) {
        setFormError(await res.text());
      } else {
        setSheetOpen(false);
        setPlayerUuid("");
        setReason("");
        setExpiresAt("");
        router.refresh();
      }
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="flex justify-end">
        {canCreate && (
          <Button size="sm" onClick={() => setSheetOpen(true)}>
            Issue Punishment
          </Button>
        )}
      </div>

      <Tabs defaultValue="punishments">
        <TabsList>
          <TabsTrigger value="punishments">Punishments</TabsTrigger>
          <TabsTrigger value="active-bans">Active Bans</TabsTrigger>
        </TabsList>

        <TabsContent value="punishments" className="mt-4">
          <div className="rounded-xl border border-border bg-card/60">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Player</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Staff</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  {canRevoke && <TableHead />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {punishments.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={canRevoke ? 7 : 6}
                      className="text-center opacity-50"
                    >
                      No punishments.
                    </TableCell>
                  </TableRow>
                ) : (
                  punishments.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs">
                        {p.player_username ?? p.player_uuid.slice(0, 8)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={SEVERITY_VARIANTS[p.type]}>
                          {p.type}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm opacity-70">
                        {p.reason}
                      </TableCell>
                      <TableCell className="text-xs opacity-60">
                        {p.staff_id ?? "—"}
                      </TableCell>
                      <TableCell className="text-xs opacity-60">
                        {formatDate(p.created_at)}
                      </TableCell>
                      <TableCell>
                        {p.revoked ? (
                          <Badge variant="outline">Revoked</Badge>
                        ) : (
                          <Badge variant="secondary">Active</Badge>
                        )}
                      </TableCell>
                      {canRevoke && (
                        <TableCell>
                          {!p.revoked && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => revoke(p.id)}
                            >
                              Revoke
                            </Button>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="active-bans" className="mt-4">
          <div className="rounded-xl border border-border bg-card/60">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Player</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Expires</TableHead>
                  {canRevoke && <TableHead />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeBans.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={canRevoke ? 5 : 4}
                      className="text-center opacity-50"
                    >
                      No active bans.
                    </TableCell>
                  </TableRow>
                ) : (
                  activeBans.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs">
                        {p.player_username ?? p.player_uuid.slice(0, 8)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="destructive">{p.type}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm opacity-70">
                        {p.reason}
                      </TableCell>
                      <TableCell className="text-xs opacity-60">
                        {formatDate(p.expires_at)}
                      </TableCell>
                      {canRevoke && (
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => revoke(p.id)}
                          >
                            Revoke
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Issue Punishment</SheetTitle>
          </SheetHeader>
          <div className="mt-4 space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-medium opacity-60">
                Player UUID
              </label>
              <Input
                placeholder="xxxxxxxx-xxxx-…"
                value={playerUuid}
                onChange={(e) => setPlayerUuid(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium opacity-60">Type</label>
              <Select
                value={type}
                onValueChange={(v) => setType(v as PunishmentType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PUNISHMENT_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium opacity-60">Reason</label>
              <Input
                placeholder="Reason for punishment"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            {(type === "BAN" || type === "TEMP_BAN") && (
              <div className="space-y-1">
                <label className="text-xs font-medium opacity-60">
                  Expires at (optional)
                </label>
                <Input
                  type="datetime-local"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                />
              </div>
            )}
            {formError && (
              <p className="text-sm text-destructive">{formError}</p>
            )}
          </div>
          <SheetFooter className="mt-6">
            <Button
              variant="ghost"
              onClick={() => setSheetOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={submitPunishment} disabled={submitting}>
              {submitting ? "Submitting…" : "Issue"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
