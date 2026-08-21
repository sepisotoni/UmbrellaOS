"use client";

import { useRouter, usePathname } from "next/navigation";
import { useState, useTransition } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { PlayerSchema } from "@/lib/types";
import { Search } from "lucide-react";

function truncateUuid(uuid: string) {
  return uuid.length > 12 ? `${uuid.slice(0, 8)}…` : uuid;
}

function formatDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString();
}

export function PlayersTable({
  players,
  initialUsername,
}: {
  players: PlayerSchema[];
  initialUsername: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState(initialUsername);
  const [, startTransition] = useTransition();

  function handleSearch(val: string) {
    setQuery(val);
    startTransition(() => {
      const params = new URLSearchParams();
      if (val) params.set("username", val);
      router.push(`${pathname}?${params.toString()}`);
    });
  }

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 opacity-40"
        />
        <Input
          className="pl-8"
          placeholder="Search by username…"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
        />
      </div>
      <div className="rounded-xl border border-border bg-card/60">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>UUID</TableHead>
              <TableHead>Last seen</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {players.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center opacity-50">
                  No players found.
                </TableCell>
              </TableRow>
            ) : (
              players.map((p) => (
                <TableRow key={p.uuid}>
                  <TableCell>
                    <Link
                      href={`/players/${p.uuid}`}
                      className="font-medium hover:underline"
                    >
                      {p.username}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs opacity-60">
                    {truncateUuid(p.uuid)}
                  </TableCell>
                  <TableCell className="text-sm opacity-70">
                    {formatDate(p.last_seen)}
                  </TableCell>
                  <TableCell>
                    {p.status ? (
                      <Badge variant="outline">{p.status}</Badge>
                    ) : (
                      <span className="opacity-40">—</span>
                    )}
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
