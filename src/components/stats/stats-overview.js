// src/components/stats/stats-overview.js
"use client"; // Required for client-side hooks and interactions

import { useState, useEffect } from "react";
// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"; // Added CardDescription
import { Skeleton } from "@/components/ui/skeleton"; // Ensure you have this component

// --- Icon Imports ---
// Using appropriate icons for each stat
import { BookOpen, Edit3, Languages, Bookmark } from "lucide-react"; // Using Edit3 for Words Written, Languages for language count, Bookmark for Vocabulary

export function StatsOverview() {
  // State for the calculated statistics
  const [stats, setStats] = useState({
    totalEntries: 0,
    totalWords: 0,
    vocabularyCount: 0,
    // streakDays: 0, // Removing simplified streak for now, needs better logic
    languagesCount: 0, // Renamed from 'languages' for clarity
  });
  // State for loading and errors
  const [isLoading, setIsLoading] = useState(true); // Renamed 'loading'
  const [error, setError] = useState(null);
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client

  // Effect hook to fetch data and calculate stats
  useEffect(() => {
    async function fetchStats() {
      setIsLoading(true);
      setError(null);
      // Reset stats to zero before fetching
      setStats({ totalEntries: 0, totalWords: 0, vocabularyCount: 0, languagesCount: 0 });

      try {
        // 1. Get user session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !session?.user) {
          throw new Error(sessionError?.message || "User not authenticated.");
        }
        const userId = session.user.id;

        // 2. Fetch necessary data in parallel
        const [entriesResponse, vocabResponse] = await Promise.all([
          // Fetch entries: select needed fields
          supabase
            .from("entries")
            .select("id, content, language") // Only select content, language, and id (for count)
            .eq("user_id", userId),
          // Fetch vocabulary count directly (more efficient)
          supabase
            .from("vocabulary")
            .select('id', { count: 'exact', head: true }) // Use count='exact' for efficiency
            .eq("user_id", userId)
        ]);

        // Handle errors from fetches
        if (entriesResponse.error) throw entriesResponse.error;
        if (vocabResponse.error) throw vocabResponse.error;

        const entries = entriesResponse.data || [];
        const vocabularyCount = vocabResponse.count || 0;

        // 3. Perform calculations client-side
        // Note: For very large datasets, consider database functions/views for performance.

        // Calculate total word count
        const totalWords = entries.reduce((acc, entry) => {
          // Basic word count - splits by whitespace, filters out empty strings
          const words = entry.content?.split(/\s+/).filter(Boolean) || [];
          return acc + words.length;
        }, 0);

        // Calculate unique languages used
        const uniqueLanguages = new Set(entries.map(entry => entry.language).filter(Boolean)); // Filter out null/empty languages

        // Calculate streak (This requires more complex logic involving dates,
        // fetching created_at, comparing consecutive days. Omitted for simplicity now,
        // recommend implementing this server-side or with careful date logic.)
        // let streakDays = calculateStreak(entries); // Placeholder for complex function

        // 4. Update state with calculated stats
        setStats({
          totalEntries: entries.length,
          totalWords,
          vocabularyCount,
          languagesCount: uniqueLanguages.size,
          // streakDays, // Add back when implemented
        });

      } catch (err) {
        console.error("Error fetching stats overview:", err);
        setError(err.message || "Failed to load overview statistics.");
        // Reset stats on error
        setStats({ totalEntries: 0, totalWords: 0, vocabularyCount: 0, languagesCount: 0 });
      } finally {
        setIsLoading(false); // Finish loading
      }
    }

    fetchStats();
    // Add supabase dependency
  }, [supabase]);

  // --- Render Loading State ---
  if (isLoading) {
    // Render skeletons matching the card layout
    return (
      <>
        <Card>
           <CardHeader className="pb-2">
             <Skeleton className="h-4 w-2/5" />
           </CardHeader>
           <CardContent>
             <Skeleton className="h-8 w-1/2 mb-1" />
             <Skeleton className="h-3 w-3/5" />
           </CardContent>
         </Card>
         <Card>
           <CardHeader className="pb-2">
             <Skeleton className="h-4 w-2/5" />
           </CardHeader>
           <CardContent>
             <Skeleton className="h-8 w-1/2 mb-1" />
             <Skeleton className="h-3 w-3/5" />
           </CardContent>
         </Card>
         <Card>
           <CardHeader className="pb-2">
             <Skeleton className="h-4 w-2/5" />
           </CardHeader>
           <CardContent>
             <Skeleton className="h-8 w-1/2 mb-1" />
             <Skeleton className="h-3 w-3/5" />
           </CardContent>
         </Card>
         <Card>
           <CardHeader className="pb-2">
             <Skeleton className="h-4 w-2/5" />
           </CardHeader>
           <CardContent>
             <Skeleton className="h-8 w-1/2 mb-1" />
             <Skeleton className="h-3 w-3/5" />
           </CardContent>
         </Card>
      </>
    );
  }

   // --- Render Error State ---
   if (error) {
     return (
       <div className="col-span-full rounded-md border border-destructive bg-destructive/10 p-4 text-center text-destructive">
         <p>Could not load stats: {error}</p>
       </div>
     );
   }

  // --- Render Statistics Cards ---
  // Using React.Fragment shorthand <> to return multiple cards directly for grid layout
  return (
    <>
      {/* Total Entries Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Entries</CardTitle>
          <BookOpen className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalEntries}</div>
           <p className="text-xs text-muted-foreground">
             Journal entries created
           </p>
        </CardContent>
      </Card>

      {/* Words Written Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Words Written</CardTitle>
          <Edit3 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalWords.toLocaleString()}</div> {/* Format large numbers */}
           <p className="text-xs text-muted-foreground">
             {/* Calculate average words/entry, handle division by zero */}
             ~{Math.round(stats.totalWords / Math.max(stats.totalEntries, 1)).toLocaleString()} words per entry
           </p>
        </CardContent>
      </Card>

      {/* Vocabulary Count Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Vocabulary Saved</CardTitle>
          <Bookmark className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.vocabularyCount}</div>
          <p className="text-xs text-muted-foreground">
            Unique words extracted
          </p>
        </CardContent>
      </Card>

       {/* Languages Used Card */}
       <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Languages Practiced</CardTitle>
          <Languages className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.languagesCount}</div>
          <p className="text-xs text-muted-foreground">
            Different languages used in entries
          </p>
        </CardContent>
      </Card>

      {/* Optional: Add Streak Card back when logic is implemented */}
      {/*
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Current Streak</CardTitle>
          <Calendar className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.streakDays} days</div>
          <p className="text-xs text-muted-foreground">
            Consecutive days with an entry
          </p>
        </CardContent>
      </Card>
      */}
    </>
  );
}