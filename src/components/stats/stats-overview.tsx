"use client";

import { useState, useEffect } from "react";
import { createSupabaseClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, Calendar, Vocabulary } from "lucide-react";

export function StatsOverview() {
  const [stats, setStats] = useState({
    totalEntries: 0,
    totalWords: 0,
    vocabularyCount: 0,
    streakDays: 0,
    languages: 0,
  });
  const [loading, setLoading] = useState(true);
  const supabase = createSupabaseClient();

  useEffect(() => {
    async function fetchStats() {
      try {
        const { data: user } = await supabase.auth.getUser();
        
        if (!user.user) {
          return;
        }

        // Fetch entries
        const { data: entries, error: entriesError } = await supabase
          .from("entries")
          .select("id, content, language, created_at")
          .eq("user_id", user.user.id);

        if (entriesError) {
          throw entriesError;
        }

        // Fetch vocabulary
        const { data: vocabulary, error: vocabError } = await supabase
          .from("vocabulary")
          .select("id")
          .eq("user_id", user.user.id);

        if (vocabError) {
          throw vocabError;
        }

        // Calculate word count from entries
        const totalWords = entries?.reduce((acc, entry) => {
          return acc + entry.content.split(/\s+/).filter(Boolean).length;
        }, 0) || 0;

        // Calculate unique languages
        const uniqueLanguages = new Set(entries?.map(entry => entry.language) || []);

        // Calculate streak (simplified - just counting consecutive days with entries)
        let streakDays = 0;
        if (entries && entries.length > 0) {
          const dates = entries.map(entry => 
            new Date(entry.created_at).toISOString().split('T')[0]
          );
          const uniqueDates = [...new Set(dates)].sort();
          
          // Simple implementation - this would need to be more sophisticated in production
          streakDays = Math.min(uniqueDates.length, 7); // Capping at 7 for demo
        }

        setStats({
          totalEntries: entries?.length || 0,
          totalWords,
          vocabularyCount: vocabulary?.length || 0,
          streakDays,
          languages: uniqueLanguages.size,
        });
      } catch (error) {
        console.error("Error fetching stats:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  if (loading) {
    return (
      <>
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Entries</CardTitle>
          <BookOpen className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalEntries}</div>
          <p className="text-xs text-muted-foreground">
            Across {stats.languages} different languages
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Words Written</CardTitle>
          <BookOpen className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalWords}</div>
          <p className="text-xs text-muted-foreground">
            ~{Math.round(stats.totalWords / Math.max(stats.totalEntries, 1))} words per entry
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Vocabulary</CardTitle>
          <Vocabulary className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.vocabularyCount}</div>
          <p className="text-xs text-muted-foreground">
            Words extracted and saved
          </p>
        </CardContent>
      </Card>
    </>
  );
}