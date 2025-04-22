// src/lib/supabase/client.js

import { createBrowserClient, createServerClient } from '@supabase/ssr';

// --- Browser Client Setup ---

// Use a module-level variable to store the singleton instance.
let browserClientInstance = null;

/**
 * Creates and/or returns a singleton instance of the Supabase browser client.
 * This ensures only one instance is active in the browser context, preventing
 * potential issues with multiple instances managing the same session/storage.
 *
 * @returns {SupabaseClient} The Supabase browser client instance.
 * @throws {Error} If Supabase environment variables are missing.
 */
export const createSupabaseBrowserClient = () => {
  if (browserClientInstance) {
    return browserClientInstance;
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl) {
    console.error('>>> ERROR: Missing environment variable NEXT_PUBLIC_SUPABASE_URL');
    throw new Error('Missing Supabase URL environment variable');
  }
  if (!supabaseKey) {
    console.error('>>> ERROR: Missing environment variable NEXT_PUBLIC_SUPABASE_ANON_KEY');
    throw new Error('Missing Supabase Anon Key environment variable');
  }

  browserClientInstance = createBrowserClient(supabaseUrl, supabaseKey);

  console.log(">>> Supabase Browser Client Initialized (Singleton)");
  return browserClientInstance;
};

// --- Server Client Setup ---

/**
 * Creates a new Supabase server-side client for API Routes and Server Components.
 * @param {import('next/headers').cookies} cookies - The cookies object from Next.js request handling
 * @returns {SupabaseClient} - A Supabase client instance configured for server-side usage.
 * @throws {Error} If environment variables are missing.
 */
export const createSupabaseServerClient = (cookies) => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    console.error('>>> ERROR: Missing environment variables for Supabase Server Client');
    throw new Error('Missing Supabase environment variables');
  }

  return createServerClient(supabaseUrl, supabaseKey, { cookies });
};