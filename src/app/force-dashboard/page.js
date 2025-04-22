// src/app/force-dashboard/page.js
"use client";

import { useEffect } from 'react';
import { createSupabaseClient } from '@/lib/supabase/client';

export default function ForceDashboardPage() {
  useEffect(() => {
    const checkAuthAndRedirect = async () => {
      const supabase = createSupabaseClient();
      const { data } = await supabase.auth.getSession();
      
      console.log("Session data:", data);
      
      if (data.session) {
        // User is authenticated, redirect to dashboard
        window.location.href = '/dashboard/dashboard';
      }
    };
    
    checkAuthAndRedirect();
  }, []);
  
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Redirecting to Dashboard...</h1>
      <p>If you're not redirected, <a href="/dashboard/dashboard" className="text-blue-500 underline">click here</a>.</p>
    </div>
  );
}