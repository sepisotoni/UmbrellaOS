"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
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
import { FlaggedPlayerSchema, AltGroupSchema } from "@/lib/types";

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const variant =
    pct >= 80 ? "destructive" : pct >= 50 ? "secondary" : "outline";
  return <Badge variant={variant}>{pct}%</Badge>;
}

export function AltDetectionView({
  flagged,
  groups,
  token,
  canManage,
}: {
  flagged: FlaggedPlayerSchema[];
  groups: AltGroupSchema[];
  token: string;
  canManage: boolean;
}) {
  const router = useRouter();

  async function markFalsePositive(uuid: string) {
    try {
      const res = await fetch(`/api/alt-false-positive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_uuid: uuid, event_ids: [], token }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-card/60">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-sm font-medium">Flagged Players</p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>Suspicion Score</TableHead>
              <TableHead>Flags</TableHead>
              {canManage && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {flagged.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={canManage ? 4 : 3}
                  className="text-center opacity-50"
                >
                  No flagged players.
                </TableCell>
              </TableRow>
            ) : (
              flagged.map((p) => (
                <TableRow key={p.uuid}>
                  <TableCell>
                    <Link
                      href={`/players/${p.uuid}`}
                      className="font-medium hover:underline"
                    >
                      {p.username}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <ScoreBadge score={p.suspicion_score} />
                  </TableCell>
                  <TableCell className="text-sm opacity-70">
                    {p.flags_count}
                  </TableCell>
                  {canManage && (
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => markFalsePositive(p.uuid)}
                      >
                        Mark false positive
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="rounded-xl border border-border bg-card/60">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-sm font-medium">Known Alt Groups</p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Group ID</TableHead>
              <TableHead>Members</TableHead>
              <TableHead>Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center opacity-50">
                  No alt groups.
                </TableCell>
              </TableRow>
            ) : (
              groups.map((g) => (
                <TableRow key={g.id}>
                  <TableCell className="font-mono text-xs opacity-60">
                    {g.id.slice(0, 8)}
                  </TableCell>
                  <TableCell className="text-sm">
                    {g.members.length} accounts
                  </TableCell>
                  <TableCell>
                    <ScoreBadge score={g.confidence} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
