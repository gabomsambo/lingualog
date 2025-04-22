import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseClient } from "@/lib/supabase/client";

// This middleware protects all routes under /dashboard
export async function middleware(request: NextRequest) {
  // Create a Supabase client
  const supabase = createSupabaseClient();

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