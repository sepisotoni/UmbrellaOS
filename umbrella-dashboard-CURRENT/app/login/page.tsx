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
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#070914] px-4 text-[#eef0ff]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(92,59,180,0.16),transparent_34%)]" />
      <div className="relative flex w-full max-w-[282px] flex-col items-center gap-5 rounded-[9px] border border-[#27304f] bg-[#070914]/90 px-8 py-10 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
        <h1 className="text-[20px] font-semibold tracking-[-0.02em]">UmbrellaOS</h1>
        <p className="text-center text-[14px] text-[#a2a7b8]">Sign in with Discord to continue.</p>
        <LoginButton nextPath={next ?? "/dashboard"} />
      </div>
    </main>
  );
}
