// src/components/entries/entry-list.tsx
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { format } from "date-fns"; // Ensure date-fns is installed (npm install date-fns)
// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton"; // Make sure you have this component
import { Button } from "@/components/ui/button"; // Import Button

// Define the structure of an entry fetched for the list
// Only include fields needed for the list display
type EntryListItem = {
  id: string;
  title: string;
  language: string;
  created_at: string; // Keep as string, format on render
  // Optionally add a content snippet if needed for display, otherwise omit
  // content: string;
};

export function EntryList() {
  // State for entries, loading status, and potential errors
  const [entries, setEntries] = useState<EntryListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true); // Renamed 'loading' to 'isLoading' for consistency
  const [error, setError] = useState<string | null>(null);
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client

  // Effect hook to fetch entries when the component mounts or supabase client changes
  useEffect(() => {
    async function fetchEntries() {
      setIsLoading(true); // Set loading true at the start of fetch
      setError(null); // Reset error state

      try {
        // 1. Get the current user session
        // Using getSession() is generally preferred over getUser() in components
        // as it handles token refreshing automatically with @supabase/ssr clients.
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        // Handle cases where there's no session or an error fetching it
        if (sessionError) {
          console.error("Session Error:", sessionError.message);
          throw new Error("Could not retrieve user session.");
        }
        if (!session?.user) {
          // This shouldn't happen if middleware is working, but good practice to check
          console.log("No user session found client-side.");
          throw new Error("User not authenticated.");
        }

        // 2. Fetch entries specifically for the logged-in user
        const userId = session.user.id;
        const { data, error: fetchError } = await supabase
          .from('entries') // Ensure 'entries' matches your Supabase table name
          .select('id, title, language, created_at') // Select only necessary columns for the list
          .eq('user_id', userId) // *** CRITICAL: Filter entries by the logged-in user's ID ***
          .order('created_at', { ascending: false }) // Order by newest first
          .limit(20); // Add a limit for pagination later if needed

        // Handle errors during the fetch
        if (fetchError) {
          console.error("Error fetching entries:", fetchError);
          throw fetchError; // Propagate the error to the catch block
        }

        // Update state with the fetched entries (or an empty array if null)
        setEntries(data || []);

      } catch (err: any) {
        // Set error state if any step fails
        setError(err.message || "An unexpected error occurred while fetching entries.");
        setEntries([]); // Clear entries on error
      } finally {
        // Ensure loading state is set to false after fetch completes (success or error)
        setIsLoading(false);
      }
    }

    fetchEntries(); // Call the fetch function

    // Add supabase to dependency array. The singleton pattern ensures this doesn't cause infinite loops.
  }, [supabase]);

  // --- Render Loading State ---
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Render multiple skeletons for better loading perception */}
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={`skeleton-${i}`}>
            <CardHeader>
              <Skeleton className="h-6 w-3/4 mb-2" /> {/* Skeleton for title */}
              <Skeleton className="h-4 w-1/2" /> {/* Skeleton for description */}
            </CardHeader>
            <CardContent>
              <Skeleton className="h-10 w-full" /> {/* Skeleton for content/button */}
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // --- Render Error State ---
  if (error) {
    return (
      <div className="rounded-md border border-destructive bg-destructive/10 p-4 text-center text-destructive">
        <p>Error loading your entries:</p>
        <p className="text-sm">{error}</p>
        {/* Optionally add a retry button */}
      </div>
    );
  }

  // --- Render Empty State ---
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <h3 className="text-lg font-semibold">No Journal Entries Yet</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Ready to start journaling in your target language?
        </p>
        <Button asChild className="mt-4">
            {/* Use Link within Button via asChild for proper styling and semantics */}
           <Link href="/entries/new">Create Your First Entry</Link>
        </Button>
      </div>
    );
  }

  // --- Render Entries List ---
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {entries.map((entry) => (
        // Wrap the Card in a Link component to make the whole card clickable
        <Link href={`/entries/${entry.id}`} key={entry.id} className="block hover:no-underline">
          <Card className="h-full overflow-hidden transition-shadow duration-200 hover:shadow-lg">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg truncate">{entry.title || "Untitled Entry"}</CardTitle>
              <CardDescription className="text-xs">
                 {/* Format the date nicely */}
                {entry.language} - {format(new Date(entry.created_at), "PP")} {/* e.g., Apr 22, 2025 */}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* You might want to display a content snippet here later */}
              {/* <p className="line-clamp-3 text-sm text-muted-foreground mb-4">
                {entry.content || "No content preview available."}
              </p> */}
              {/* A button isn't strictly needed if the whole card links, but can be explicit */}
               <Button variant="outline" size="sm" className="mt-2 w-full" tabIndex={-1}>
                 View Details
               </Button>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}