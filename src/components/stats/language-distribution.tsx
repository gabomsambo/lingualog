"use client";

import { useState, useEffect } from "react";
import { createSupabaseClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";

type DataPoint = {
  name: string;
  value: number;
};

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#FF6B6B", "#6B8E23", "#9932CC", "#008080", "#CD5C5C"];

export function LanguageDistribution() {
  const [data, setData] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const supabase = createSupabaseClient();

  useEffect(() => {
    async function fetchLanguageDistribution() {
      try {
        const { data: user } = await supabase.auth.getUser();
        
        if (!user.user) {
          return;
        }
        
        // Fetch entries
        const { data: entries, error } = await supabase
          .from("entries")
          .select("language")
          .eq("user_id", user.user.id);

        if (error) {
          throw error;
        }

        // Count entries by language
        const languageCounts: Record<string, number> = {};
        
        entries?.forEach(entry => {
          const lang = entry.language;
          languageCounts[lang] = (languageCounts[lang] || 0) + 1;
        });
        
        // Convert to array for chart
        const chartData = Object.entries(languageCounts).map(([name, value]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1), // Capitalize first letter
          value,
        }));
        
        // Sort by count descending
        chartData.sort((a, b) => b.value - a.value);
        
        setData(chartData);
      } catch (error) {
        console.error("Error fetching language distribution:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchLanguageDistribution();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Language Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Language Distribution</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center items-center h-[300px]">
          <p className="text-muted-foreground">No entries yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Language Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => [`${value} entries`, 'Count']} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}