// src/middleware.js
import { NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'

export async function middleware(request) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  // Create a Supabase client configured to use cookies from the request/response
  const supabase = createServerClient(
    // Ensure these environment variables are correctly set in your deployment environment
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        // Define how to get cookies from the request
        get(name) {
          return request.cookies.get(name)?.value
        },
        // Define how to set cookies on the response
        set(name, value, options) {
          // If the cookie is set, update the request cookies object.
          // This is necessary for the server client to be aware of changes made during the request.
          request.cookies.set({
            name,
            value,
            ...options,
          })
          // Clone the response to be able to modify its headers/cookies
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          // Set the cookie on the response
          response.cookies.set({
            name,
            value,
            ...options,
          })
        },
        // Define how to remove cookies from the response
        remove(name, options) {
          // If the cookie is removed, update the request cookies object.
          request.cookies.set({
            name,
            value: '', // Set value to empty to effectively remove
            ...options,
          })
          // Clone the response to be able to modify its headers/cookies
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          // Set the cookie on the response with an expiration date in the past to remove it
          response.cookies.set({
            name,
            value: '',
            ...options,
          })
        },
      },
    }
  )

  // Attempt to retrieve the user's session.
  // This method automatically refreshes the session token if it's expired.
  const {
    data: { session },
    error, // Catch potential errors during session retrieval
  } = await supabase.auth.getSession()

  // --- Optional Debugging Logs ---
  const requestedPath = request.nextUrl.pathname;
  console.log(`[Middleware] Path requested: ${requestedPath}`);
  console.log(`[Middleware] Session successfully retrieved: ${!!session}`);
  if (error) {
     console.error("[Middleware] Error retrieving session:", error.message);
  }
  // --- End Debugging Logs ---

  // Define which routes are considered protected (require login)
  const isProtectedRoute = requestedPath.startsWith('/dashboard') ||
                           requestedPath.startsWith('/entries') ||
                           requestedPath.startsWith('/vocabulary') ||
                           requestedPath.startsWith('/stats');

  // Define which routes are for authentication (login/signup pages)
  const isAuthRoute = requestedPath === '/auth/sign-in' || requestedPath === '/auth/sign-up';

  // --- Authentication Enforcement Logic ---

  // Scenario 1: User is NOT logged in (no session) AND is trying to access a protected route
  if (!session && isProtectedRoute) {
    console.log("[Middleware] No session found. Redirecting unauthenticated user to sign-in page.");
    // Construct the sign-in URL
    const redirectUrl = new URL('/auth/sign-in', request.url)
    // Optionally, add the original destination as a query parameter for redirecting back after login
    // redirectUrl.searchParams.set('redirect_to', requestedPath)
    // Perform the redirect
    return NextResponse.redirect(redirectUrl)
  }

  // Scenario 2: User IS logged in (session exists) AND is trying to access an auth page (sign-in/sign-up)
  if (session && isAuthRoute) {
    console.log("[Middleware] Authenticated user accessing auth page. Redirecting to dashboard.");
    // Construct the dashboard URL (adjust if your main dashboard page is different)
    const redirectUrl = new URL('/dashboard', request.url)
    // Perform the redirect
    return NextResponse.redirect(redirectUrl)
  }

  // --- If none of the above conditions are met, allow the request to proceed ---
  console.log("[Middleware] No redirection needed. Proceeding to the requested route.");
  // Return the potentially modified response (important for cookie updates)
  return response
}

// --- Matcher Configuration ---
// Define which paths will trigger this middleware function
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - debug (your debug page)
     * - public files (files with extensions like .png, .jpg, etc.)
     * - / (root path - assumes a public landing page; remove from exclusion if root is protected)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|debug|.*\\.\\w+$).*)', // Match most paths
    // Explicitly include auth routes to ensure the redirect logic for logged-in users runs
    '/auth/sign-in',
    '/auth/sign-up',
  ],
}