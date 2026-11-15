import { createClient } from '@supabase/supabase-js';

export type SupabaseClient = ReturnType<typeof createClient>;

export let supabase: SupabaseClient | null = null;

export function initializeSupabase(url: string, publishableKey: string): SupabaseClient {
  if (!url.trim() || !publishableKey.trim()) {
    throw new Error('Core returned incomplete Supabase Auth configuration');
  }
  if (supabase) return supabase;

  supabase = createClient(url, publishableKey, {
    auth: {
      flowType: 'pkce',
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  });
  return supabase;
}
