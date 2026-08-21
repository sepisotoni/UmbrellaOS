"use client";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SecurityEvent } from "@/lib/types";

const SEVERITY_VARIANTS: Record<
  string,
  "outline" | "secondary" | "destructive"
> = {
  LOW: "outline",
  MEDIUM: "secondary",
  HIGH: "destructive",
  CRITICAL: "destructive",
};

function formatDate(d: string) {
  return new Date(d).toLocaleString();
}

const SEVERITIES = ["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

export function SecurityEventsTable({ events }: { events: SecurityEvent[] }) {
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");

  const filtered =
    severityFilter === "ALL"
      ? events
      : events.filter((e) => e.severity === severityFilter);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SEVERITIES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-xl border border-border bg-card/60">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Event Type</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Severity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center opacity-50">
                  No security events.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="text-xs opacity-60">
                    {formatDate(e.timestamp)}
                  </TableCell>
                  <TableCell className="text-sm font-medium">
                    {e.event_type}
                  </TableCell>
                  <TableCell className="text-sm opacity-70">
                    {e.actor ?? "—"}
                  </TableCell>
                  <TableCell className="text-sm opacity-70">
                    {e.target ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={SEVERITY_VARIANTS[e.severity] ?? "outline"}
                    >
                      {e.severity}
                    </Badge>
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
