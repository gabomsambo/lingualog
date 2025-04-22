"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { createSupabaseClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Entry = {
  id: string;
  title: string;
  language: string;
  created_at: string;
  content: string;
};

export function EntryList() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const supabase = createSupabaseClient();

  useEffect(() => {
    async function fetchEntries() {
      try {
        const { data: user } = await supabase.auth.getUser();
        
        if (!user.user) {
          return;
        }

        const { data, error } = await supabase
          .from("entries")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(10);

        if (error) {
          throw error;
        }

        setEntries(data || []);
      } catch (error) {
        console.error("Error fetching entries:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchEntries();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="overflow-hidden">
            <CardHeader className="pb-2">
              <Skeleton className="h-5 w-1/2" />
              <Skeleton className="h-4 w-1/4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-20 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <h3 className="text-lg font-medium">No entries yet</h3>
        <p className="text-sm text-muted-foreground">
          Start your language learning journey by creating a new entry.
        </p>
        <Link href="/entries/new" className="mt-4">
          <button className="text-primary underline-offset-4 hover:underline">
            Create your first entry
          </button>
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {entries.map((entry) => (
        <Link href={`/entries/${entry.id}`} key={entry.id}>
          <Card className="overflow-hidden transition-shadow hover:shadow-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{entry.title}</CardTitle>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">
                  {entry.language}
                </span>
                <span className="text-xs text-muted-foreground">
                  {format(new Date(entry.created_at), "MMM d, yyyy")}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <p className="line-clamp-3 text-sm text-muted-foreground">
                {entry.content}
              </p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}