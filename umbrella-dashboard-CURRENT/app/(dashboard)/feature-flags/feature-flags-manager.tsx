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
import { FeatureFlagResponse } from "@/lib/types";

function formatDate(d: string) {
  return new Date(d).toLocaleDateString();
}

export function FeatureFlagsManager({
  flags,
  token,
  canManage,
}: {
  flags: FeatureFlagResponse[];
  token: string;
  canManage: boolean;
}) {
  const router = useRouter();
  const [newName, setNewName] = useState("");
  const [newEnabled, setNewEnabled] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  async function toggle(name: string, enabled: boolean) {
    try {
      const res = await fetch(`/api/feature-flag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, enabled, token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Toggle failed");
    }
  }

  async function deleteFlag(name: string) {
    try {
      const res = await fetch(`/api/feature-flag`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function createFlag() {
    if (!newName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await fetch(`/api/feature-flag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim(), enabled: newEnabled, token }),
      });
      if (!res.ok) {
        setCreateError(await res.text());
      } else {
        setNewName("");
        router.refresh();
      }
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      {canManage && (
        <div className="rounded-xl border border-border bg-card/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide opacity-50 mb-3">
            New Flag
          </p>
          <div className="flex gap-2 items-center flex-wrap">
            <Input
              placeholder="flag-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="max-w-xs"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setNewEnabled((v) => !v)}
            >
              {newEnabled ? "Enabled" : "Disabled"}
            </Button>
            <Button size="sm" onClick={createFlag} disabled={creating || !newName.trim()}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </div>
          {createError && (
            <p className="mt-2 text-sm text-destructive">{createError}</p>
          )}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card/60">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              {canManage && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {flags.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={canManage ? 4 : 3}
                  className="text-center opacity-50"
                >
                  No feature flags.
                </TableCell>
              </TableRow>
            ) : (
              flags.map((f) => (
                <TableRow key={f.name}>
                  <TableCell className="font-mono text-sm">{f.name}</TableCell>
                  <TableCell>
                    <Badge variant={f.enabled ? "secondary" : "outline"}>
                      {f.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs opacity-60">
                    {formatDate(f.created_at)}
                  </TableCell>
                  {canManage && (
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggle(f.name, !f.enabled)}
                        >
                          {f.enabled ? "Disable" : "Enable"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteFlag(f.name)}
                        >
                          Delete
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
    </div>
  );
}
