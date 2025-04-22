import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Create a Supabase client without relying on the helpers
const createSupabase = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  return createClient(supabaseUrl, supabaseKey);
};

// This middleware protects all routes under /dashboard
export async function middleware(request) {
  // Create a Supabase client
  const supabase = createSupabase();

  // Refresh session if available
  const { data: { session } } = await supabase.auth.getSession();

  // If user is not signed in and trying to access a protected route
  if (!session?.user && request.nextUrl.pathname.startsWith("/dashboard")) {
    // Redirect to the sign-in page
    const redirectUrl = new URL("/sign-in", request.url);
    return NextResponse.redirect(redirectUrl);
  }

  // If user is signed in and trying to access auth pages
  if (session?.user && 
      (request.nextUrl.pathname.startsWith("/sign-in") || 
       request.nextUrl.pathname.startsWith("/sign-up"))) {
    // Redirect to the dashboard
    const redirectUrl = new URL("/dashboard", request.url);
    return NextResponse.redirect(redirectUrl);
  }

  return NextResponse.next();
}

// Specify which routes this middleware should run on
export const config = {
  matcher: [
    "/dashboard/:path*",
    "/entries/:path*",
    "/vocabulary/:path*",
    "/stats/:path*",
    "/sign-in",
    "/sign-up",
  ],
};