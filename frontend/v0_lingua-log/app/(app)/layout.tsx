"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSession } from "@/lib/auth";
import { supabase } from "@/lib/supabase";
import type React from "react"
import { MainNav } from "@/components/main-nav"
import { UserNav } from "@/components/user-nav"

export default function AppGroupLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function checkAuth() {
      try {
        const session = await getSession();
        
        if (!session) {
          // Redirect to login if no session
          router.push("/auth/sign-in");
          return;
        }
        
        // Set up auth state change listener
        const { data: authListener } = supabase.auth.onAuthStateChange(
          (event, session) => {
            if (event === "SIGNED_OUT") {
              router.push("/auth/sign-in");
            }
          }
        );
        
        setIsLoading(false);
        
        // Clean up the listener on unmount
        return () => {
          authListener.subscription.unsubscribe();
        };
      } catch (error) {
        console.error("Auth check error:", error);
        router.push("/auth/sign-in");
      }
    }
    
    checkAuth();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading your journal...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-50 w-full border-b-2 border-white/10 bg-gradient-to-r from-fun-blue/20 via-fun-purple/20 to-fun-pink/20 backdrop-blur supports-[backdrop-filter]:bg-white/60 shadow-md">
        <div className="container flex h-16 items-center">
          <div className="mr-4 flex">
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-fun-blue via-fun-purple to-fun-pink bg-clip-text text-transparent">
              LinguaLog
            </h1>
          </div>
          <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
            <div className="w-full flex-1 md:w-auto md:flex-none">{/* Search or other elements could go here */}</div>
            <MainNav />
            <div className="flex items-center space-x-2">
              <UserNav />
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 bg-gradient-to-br from-white via-fun-blue/5 to-fun-purple/5">
        <div className="container py-8">{children}</div>
      </main>
    </div>
  )
} 