"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Get the URL params
        const { searchParams } = new URL(window.location.href);
        const code = searchParams.get('code');

        if (code) {
          // Exchange the auth code for a session
          await supabase.auth.exchangeCodeForSession(code);

          // Check if we have a valid session
          const { data } = await supabase.auth.getSession();
          
          if (data.session) {
            // If we have a session, redirect to the dashboard
            router.push("/dashboard");
          } else {
            // If not, redirect to sign in
            router.push("/auth/sign-in");
          }
        }
      } catch (error) {
        console.error('Error handling auth callback:', error);
        router.push("/auth/sign-in");
      }
    };

    handleAuthCallback();
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Authenticating...</h2>
        <p>Please wait while we authenticate your account.</p>
      </div>
    </div>
  );
} 