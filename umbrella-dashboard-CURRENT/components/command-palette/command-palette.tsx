"use client";

// components/command-palette/command-palette.tsx — the whole command
// palette is one 'use client' leaf (Decision 6: scope client components to
// genuinely interactive leaves). It calls same-origin /api/search, never
// umbrella-core directly — see app/api/search/route.ts's comment for why.
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { SearchResultItem } from "@/lib/search-types";

const DEBOUNCE_MS = 150;

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef(0);
  const router = useRouter();

  // Global Cmd+K / Ctrl+K to open, Escape to close, plus a custom event so
  // a click affordance (Topbar's search button) can open it too without
  // needing shared React state between two independently-mounted leaves.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    }
    function onOpenEvent() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("umbrella:open-command-palette", onOpenEvent);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("umbrella:open-command-palette", onOpenEvent);
    };
  }, []);

  // Reset state whenever the palette closes, so reopening it starts fresh.
  // Done during render (React's documented "adjusting state when a prop
  // changes" pattern: https://react.dev/learn/you-might-not-need-an-effect
  // #adjusting-some-state-when-a-prop-changes), not in an effect — an
  // effect here would fire a render *after* the close-triggered render,
  // which is exactly the cascading-render pattern
  // react-hooks/set-state-in-effect exists to catch. `wasOpen` only tracks
  // the previous `open` value to detect the true->false transition; it's
  // not itself meaningful application state.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (!open) {
      setQuery("");
      setResults([]);
      setActiveIndex(0);
    }
  }

  // Debounced federated fetch, per keystroke (roadmap Decision 3: live
  // fan-out, no pre-built index) — debounce here just avoids firing on
  // every single keystroke of a fast typist, it does not change the
  // "no index" model at all, the backend is still hit live per search.
  //
  // Neither the too-short-query case nor the loading indicator is set
  // synchronously in this effect's body anymore (both were
  // react-hooks/set-state-in-effect violations — real cascading-render
  // bugs, not lint noise). The too-short case is derived at render time
  // via `visibleResults`/`isSearching` below. `setLoading(true)` now
  // happens inside the debounce timeout's callback, right as the actual
  // fetch begins — which is also a small UX improvement on top of being
  // correct: no loading flash for a query that never survives the
  // debounce window.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      return;
    }
    const thisRequestId = ++requestIdRef.current;
    debounceRef.current = setTimeout(async () => {
      if (thisRequestId !== requestIdRef.current) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const body = (await res.json()) as { results: SearchResultItem[] };
        // Ignore stale responses that resolve out of order.
        if (thisRequestId === requestIdRef.current) {
          setResults(body.results);
          setActiveIndex(0);
        }
      } catch {
        if (thisRequestId === requestIdRef.current) setResults([]);
      } finally {
        if (thisRequestId === requestIdRef.current) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const trimmedQuery = query.trim();
  const queryTooShort = trimmedQuery.length < 2;
  const visibleResults = queryTooShort ? [] : results;
  const isSearching = !queryTooShort && loading;

  const navigateTo = useCallback(
    (item: SearchResultItem) => {
      setOpen(false);
      router.push(item.href);
    },
    [router]
  );

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, visibleResults.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && visibleResults[activeIndex]) {
      navigateTo(visibleResults[activeIndex]);
    }
  }

  if (!open) return null;

  const grouped = groupBySource(visibleResults);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-24"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onInputKeyDown}
          placeholder="Search players, knowledge base, logs, marketplace…"
          className="w-full border-b border-[var(--border)] bg-transparent px-4 py-3 text-sm outline-none"
        />
        <div className="max-h-80 overflow-y-auto py-1">
          {isSearching && <p className="px-4 py-3 text-xs opacity-50">Searching…</p>}
          {!isSearching && !queryTooShort && visibleResults.length === 0 && (
            <p className="px-4 py-3 text-xs opacity-50">No results.</p>
          )}
          {grouped.map(([sourceLabel, items]) => (
            <div key={sourceLabel}>
              <p className="px-4 pt-2 text-[10px] font-medium uppercase tracking-wide opacity-40">
                {sourceLabel}
              </p>
              {items.map((item) => {
                const globalIndex = visibleResults.indexOf(item);
                return (
                  <button
                    key={`${item.sourceId}:${item.href}`}
                    onClick={() => navigateTo(item)}
                    className={`flex w-full flex-col items-start px-4 py-2 text-left text-sm ${
                      globalIndex === activeIndex ? "bg-white/10" : "hover:bg-white/5"
                    }`}
                  >
                    <span>{item.title}</span>
                    {item.subtitle && (
                      <span className="text-xs opacity-50">{item.subtitle}</span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function groupBySource(items: SearchResultItem[]): [string, SearchResultItem[]][] {
  const map = new Map<string, SearchResultItem[]>();
  for (const item of items) {
    const bucket = map.get(item.sourceLabel) ?? [];
    bucket.push(item);
    map.set(item.sourceLabel, bucket);
  }
  return Array.from(map.entries());
}
