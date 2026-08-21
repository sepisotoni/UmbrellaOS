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
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PlayerLanguageResponse, TranslateResponse } from "@/lib/types";

function formatDate(d: string) {
  return new Date(d).toLocaleDateString();
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <span className="text-xs opacity-70">{pct}%</span>
  );
}

export function TranslationView({
  languages,
  token,
}: {
  languages: PlayerLanguageResponse[];
  token: string;
}) {
  const [text, setText] = useState("");
  const [targetLang, setTargetLang] = useState("en");
  const [translating, setTranslating] = useState(false);
  const [result, setResult] = useState<TranslateResponse | null>(null);
  const [translateError, setTranslateError] = useState<string | null>(null);

  async function translate() {
    if (!text.trim()) return;
    setTranslating(true);
    setTranslateError(null);
    setResult(null);
    try {
      const res = await fetch(`/api/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim(), target_language: targetLang, token }),
      });
      if (!res.ok) {
        setTranslateError(await res.text());
      } else {
        const data = (await res.json()) as TranslateResponse;
        setResult(data);
      }
    } catch (e) {
      setTranslateError(e instanceof Error ? e.message : "Translation failed");
    } finally {
      setTranslating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-card/60 p-5 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-50">
          Manual Translation
        </p>
        <div className="flex gap-2 flex-wrap items-start">
          <Input
            placeholder="Text to translate"
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="max-w-md"
          />
          <Input
            placeholder="Target language (e.g. en)"
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className="w-40"
          />
          <Button size="sm" onClick={translate} disabled={translating || !text.trim()}>
            {translating ? "Translating…" : "Translate"}
          </Button>
        </div>
        {translateError && (
          <p className="text-sm text-destructive">{translateError}</p>
        )}
        {result && (
          <div className="rounded-lg bg-muted/30 p-3 text-sm space-y-1">
            <p className="opacity-60 text-xs">
              {result.source_language} → {result.target_language}
            </p>
            <p>{result.translated}</p>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border bg-card/60">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-sm font-medium">Player Language Preferences</p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Player UUID</TableHead>
              <TableHead>Detected Language</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Updated</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {languages.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center opacity-50">
                  No language data.
                </TableCell>
              </TableRow>
            ) : (
              languages.map((l) => (
                <TableRow key={l.player_uuid}>
                  <TableCell className="font-mono text-xs opacity-60">
                    {l.player_uuid.slice(0, 12)}…
                  </TableCell>
                  <TableCell className="text-sm font-medium">
                    {l.detected_language}
                  </TableCell>
                  <TableCell>
                    <ConfidenceBar value={l.confidence} />
                  </TableCell>
                  <TableCell className="text-xs opacity-60">
                    {formatDate(l.updated_at)}
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
