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
import { StaffMember, RoleSchema } from "@/lib/types";

export function StaffTable({
  members,
  roles,
  token,
}: {
  members: StaffMember[];
  roles: RoleSchema[];
  token: string;
}) {
  const router = useRouter();
  const [addSheet, setAddSheet] = useState(false);
  const [discordId, setDiscordId] = useState("");
  const [roleId, setRoleId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function manageStaff(
    discord_id: string,
    action: "promote" | "demote",
    role_id: string
  ) {
    try {
      const res = await fetch(`/api/staff-manage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ discord_id, action, role_id, token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Action failed");
    }
  }

  async function addStaff() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/staff-manage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          discord_id: discordId,
          action: "add",
          role_id: roleId,
          token,
        }),
      });
      if (!res.ok) {
        setError(await res.text());
      } else {
        setAddSheet(false);
        setDiscordId("");
        setRoleId("");
        router.refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setAddSheet(true)}>
          Add Staff
        </Button>
      </div>

      <div className="rounded-xl border border-border bg-card/60">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>Discord ID</TableHead>
              <TableHead>Current Role</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center opacity-50">
                  No staff members found.
                </TableCell>
              </TableRow>
            ) : (
              members.map((m) => (
                <TableRow key={m.discord_id}>
                  <TableCell className="font-medium">{m.username}</TableCell>
                  <TableCell className="font-mono text-xs opacity-60">
                    {m.discord_id}
                  </TableCell>
                  <TableCell>
                    {m.current_role ? (
                      <Badge variant="outline">{m.current_role}</Badge>
                    ) : (
                      <span className="opacity-40">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {roles[0] && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            manageStaff(m.discord_id, "promote", roles[0].id)
                          }
                        >
                          Promote
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          manageStaff(
                            m.discord_id,
                            "demote",
                            m.current_role ?? ""
                          )
                        }
                      >
                        Demote
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Sheet open={addSheet} onOpenChange={setAddSheet}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Add Staff Member</SheetTitle>
          </SheetHeader>
          <div className="mt-4 space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-medium opacity-60">
                Discord ID
              </label>
              <Input
                placeholder="Discord user ID"
                value={discordId}
                onChange={(e) => setDiscordId(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium opacity-60">Role</label>
              <Select value={roleId} onValueChange={setRoleId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((r) => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <SheetFooter className="mt-6">
            <Button variant="ghost" onClick={() => setAddSheet(false)}>
              Cancel
            </Button>
            <Button onClick={addStaff} disabled={loading}>
              {loading ? "Adding…" : "Add"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
