// src/app/auth/callback/route.js
import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers'; // Import cookies function from next/headers

/**
 * Helper function to create a Supabase client instance specifically for Route Handlers.
 * It uses the 'cookies' utility from 'next/headers' to manage session cookies server-side.
 * @returns {SupabaseClient} An instance of the Supabase client configured for server-side use.
 * @throws {Error} If Supabase environment variables are missing.
 */
function createSupabaseRouteHandlerClient() {
  const cookieStore = cookies(); // Get the cookie store for the current request

  // Ensure environment variables are available
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseKey) {
    console.error('>>> ERROR [Auth Callback]: Missing Supabase environment variables');
    throw new Error('Internal configuration error.'); // Avoid exposing details
  }

  // Create and return the server-side Supabase client
  return createServerClient(
    supabaseUrl,
    supabaseKey,
    {
      cookies: {
        // Define function to get a cookie
        get(name) {
          return cookieStore.get(name)?.value;
        },
        // Define function to set a cookie
        set(name, value, options) {
          try {
            cookieStore.set({ name, value, ...options });
          } catch (error) {
            console.error(`[Auth Callback] Failed to set cookie '${name}'. Error:`, error);
            // Handle error appropriately, maybe log it or ignore if safe
          }
        },
        // Define function to remove a cookie
        remove(name, options) {
          try {
            cookieStore.set({ name, value: '', ...options }); // Set empty value to remove
          } catch (error) {
            console.error(`[Auth Callback] Failed to remove cookie '${name}'. Error:`, error);
          }
        },
      },
    }
  );
}

// --- GET Handler for the Authentication Callback ---
export async function GET(request) {
  // Parse the incoming request URL
  const requestUrl = new URL(request.url);
  // Extract the authorization code from the query parameters
  const code = requestUrl.searchParams.get("code");
  // Extract the optional 'next' parameter for post-auth redirection, default to dashboard
  const next = requestUrl.searchParams.get('next') || '/dashboard'; // Ensure '/dashboard' is correct path

  // If an authorization code exists in the URL...
  if (code) {
    console.log("[Auth Callback] Received authorization code. Exchanging for session...");
    const supabase = createSupabaseRouteHandlerClient(); // Create the server client

    try {
      // Exchange the code for a user session. Supabase handles setting the session cookie.
      const { error } = await supabase.auth.exchangeCodeForSession(code);

      // If an error occurs during the exchange...
      if (error) {
        console.error("[Auth Callback] Code exchange failed:", error.message);
        // Redirect back to the sign-in page with an error message
        const redirectUrl = new URL('/auth/sign-in', request.url);
        redirectUrl.searchParams.set('error', 'Authentication Failed');
        redirectUrl.searchParams.set('error_description', 'Could not log you in. Please try again.');
        return NextResponse.redirect(redirectUrl);
      }
      // If successful, the session cookie is automatically handled by the client setup.
      console.log("[Auth Callback] Code exchange successful. Session established.");

    } catch (exchangeError) {
      // Catch any unexpected errors during the Supabase client interaction
      console.error("[Auth Callback] Unexpected error during code exchange:", exchangeError);
      const redirectUrl = new URL('/auth/sign-in', request.url);
      redirectUrl.searchParams.set('error', 'Server Error');
      redirectUrl.searchParams.set('error_description', 'An internal error occurred during login.');
      return NextResponse.redirect(redirectUrl);
    }
  } else {
    // Log if the callback was accessed without a code (e.g., direct navigation)
    console.warn("[Auth Callback] Accessed without an authorization code.");
    // Optionally redirect to sign-in or show an informational message
    // For now, we'll proceed to the 'next' URL anyway, as email confirmations might land here too.
  }

  // Redirect the user to their intended destination after the auth process
  console.log(`[Auth Callback] Redirecting to final destination: ${next}`);
  // Construct the final redirect URL using the original request's origin
  const finalRedirectUrl = new URL(next, requestUrl.origin);
  return NextResponse.redirect(finalRedirectUrl.toString());
}