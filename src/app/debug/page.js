// src/app/debug/page.js
"use client";

import { useEffect, useState } from 'react';
import { createSupabaseClient } from '@/lib/supabase/client';

export default function DebugPage() {
  const [sessionData, setSessionData] = useState(null);
  const [error, setError] = useState(null);
  const supabase = createSupabaseClient();
  
  useEffect(() => {
    async function checkSession() {
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          setError(error.message);
          return;
        }
        setSessionData(data);
      } catch (err) {
        setError(err.message);
      }
    }
    
    checkSession();
  }, []);
  
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Authentication Debug</h1>
      
      <div className="bg-gray-100 p-4 rounded mb-4">
        <h2 className="text-lg font-medium mb-2">Session Data:</h2>
        <pre className="whitespace-pre-wrap bg-white p-2 rounded">
          {sessionData ? JSON.stringify(sessionData, null, 2) : 'Loading...'}
        </pre>
      </div>
      
      {error && (
        <div className="bg-red-100 p-4 rounded">
          <h2 className="text-lg font-medium mb-2">Error:</h2>
          <p>{error}</p>
        </div>
      )}
      
      <div className="mt-4">
        <button 
          className="bg-blue-500 text-white px-4 py-2 rounded mr-2"
          onClick={async () => {
            const { error } = await supabase.auth.signOut();
            if (error) {
              setError(error.message);
            } else {
              window.location.reload();
            }
          }}
        >
          Sign Out
        </button>
        
        <button 
          className="bg-gray-500 text-white px-4 py-2 rounded"
          onClick={() => window.location.reload()}
        >
          Refresh
        </button>
      </div>
    </div>
  );
}