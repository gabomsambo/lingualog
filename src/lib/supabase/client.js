// src/lib/supabase/client.js
import { createBrowserClient } from '@supabase/ssr'

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
  // If an instance already exists, return it.
  if (browserClientInstance) {
    return browserClientInstance;
  }

  // Retrieve environment variables. These MUST be prefixed with NEXT_PUBLIC_
  // to be available in the browser.
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Validate that environment variables are loaded.
  if (!supabaseUrl) {
    console.error('>>> ERROR: Missing environment variable NEXT_PUBLIC_SUPABASE_URL');
    throw new Error('Missing Supabase URL environment variable');
  }
  if (!supabaseKey) {
    console.error('>>> ERROR: Missing environment variable NEXT_PUBLIC_SUPABASE_ANON_KEY');
    throw new Error('Missing Supabase Anon Key environment variable');
  }

  // Create the Supabase browser client instance using the function from @supabase/ssr.
  // Store it in the module-level variable before returning.
  browserClientInstance = createBrowserClient(supabaseUrl, supabaseKey);

  console.log(">>> Supabase Browser Client Initialized (Singleton)"); // Optional: for debugging
  return browserClientInstance;
};

/*
 * --- Deprecated / To Be Removed ---
 * The following functions are likely no longer needed or should be handled differently
 * when using the @supabase/ssr package consistently.
 */

/*
// OLD BROWSER CLIENT - Replaced by createSupabaseBrowserClient using @supabase/ssr
import { createClient } from '@supabase/supabase-js'; // Old import
export const createSupabaseClient_OLD = () => {
  // ... old implementation ...
  return createClient(supabaseUrl, supabaseKey);
};
*/

/*
// SERVER CLIENT - Generally, you should use createServerClient from '@supabase/ssr'
// directly within your server-side code (Middleware, API Routes, Server Components)
// passing the appropriate cookie store (from 'next/headers' or request/response objects).
// Using a generic server client here might bypass the SSR cookie handling.
export const createSupabaseServerClient_OLD = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  // Note: Service Role Key should NOT be exposed to the browser.
  // It should only be used in secure server environments.
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !supabaseServiceKey) {
    throw new Error('Missing Supabase environment variables for server client');
  }
  // This creates a generic client, often used with service_role key for admin tasks.
  // Be cautious using this for user authentication handling on the server, prefer createServerClient.
  return createClient(supabaseUrl, supabaseServiceKey);
};
*/

// --- How to Use in Components ---
// In your client components (.js, .jsx, .tsx):
// import { createSupabaseBrowserClient } from '@/lib/supabase/client';
// const supabase = createSupabaseBrowserClient();
// Now you can use 'supabase.auth', 'supabase.from(...)', etc.