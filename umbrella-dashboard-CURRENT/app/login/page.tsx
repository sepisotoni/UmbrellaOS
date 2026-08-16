import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { LoginButton } from "./login-button";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const session = await getSession();
  if (session) redirect("/dashboard");

  const { next } = await searchParams;

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4 rounded-lg border border-[var(--border)] p-10">
        <h1 className="text-xl font-semibold">UmbrellaOS</h1>
        <p className="text-sm opacity-70">Sign in with Discord to continue.</p>
        <LoginButton nextPath={next ?? "/dashboard"} />
      </div>
    </main>
  );
}
