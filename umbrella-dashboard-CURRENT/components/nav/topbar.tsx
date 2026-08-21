import { UserMenu } from "./user-menu";
import { SearchTrigger } from "@/components/command-palette/search-trigger";
import type { User } from "@/lib/types";

export function Topbar({ user }: { user: User }) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-[var(--border)] px-4">
      <span className="text-sm font-medium opacity-70">UmbrellaOS</span>
      <div className="flex items-center gap-3">
        <SearchTrigger />
        <UserMenu username={user.username} role={user.role} />
      </div>
    </header>
  );
}
