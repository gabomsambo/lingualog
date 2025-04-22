"use client";

import { useState, useEffect } from "react";
import { format, subDays } from "date-fns";
import { createSupabaseClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function WritingProgress() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const supabase = createSupabaseClient();

  useEffect(() => {
    async function fetchWritingProgress() {
      try {
        const { data: user } = await supabase.auth.getUser();
        
        if (!user.user) {
          return;
        }

        // Get 30 days of data
        const lastThirtyDays = Array.from({ length: 30 }, (_, i) => {
          const date = subDays(new Date(), i);
          return format(date, "yyyy-MM-dd");
        }).reverse();
        
        // Fetch entries
        const { data: entries, error } = await supabase
          .from("entries")
          .select("content, created_at")
          .eq("user_id", user.user.id)
          .gte("created_at", lastThirtyDays[0]);

        if (error) {
          throw error;
        }

        // Group entries by date and count words
        const entriesByDate = lastThirtyDays.map(date => {
          const dayEntries = entries?.filter(entry => 
            format(new Date(entry.created_at), "yyyy-MM-dd") === date
          ) || [];
          
          const wordCount = dayEntries.reduce((acc, entry) => 
            acc + entry.content.split(/\s+/).filter(Boolean).length, 0
          );

          return {
            date: format(new Date(date), "MMM d"),
            wordCount,
          };
        });

        setData(entriesByDate);
      } catch (error) {
        console.error("Error fetching writing progress:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchWritingProgress();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Writing Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Writing Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{
                top: 5,
                right: 10,
                left: 10,
                bottom: 0,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                tickMargin={10}
                tickFormatter={(value) => value}
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                tickMargin={10}
                tickFormatter={(value) => value.toString()}
              />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="wordCount"
                stroke="#8884d8"
                strokeWidth={2}
                activeDot={{ r: 8 }}
                name="Words Written"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}