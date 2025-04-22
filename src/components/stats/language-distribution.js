// src/components/stats/language-distribution.js
"use client"; // Required for client-side hooks and interactions

import { useState, useEffect } from "react";
// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"; // Added CardDescription
import { Skeleton } from "@/components/ui/skeleton"; // Ensure you have this component

// --- Chart Imports ---
// Ensure recharts is installed: npm install recharts
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";

// Predefined colors for chart segments
// Consider generating colors dynamically or using a larger palette if you expect many languages
const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#FF6B6B", "#6B8E23", "#9932CC", "#008080", "#CD5C5C", "#4682B4", "#D2691E"];

export function LanguageDistribution() {
  // State variables
  const [chartData, setChartData] = useState([]); // Data formatted for the PieChart
  const [isLoading, setIsLoading] = useState(true); // Loading state
  const [error, setError] = useState(null); // Error state
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client

  // Effect hook to fetch and process language data
  useEffect(() => {
    async function fetchLanguageDistribution() {
      setIsLoading(true);
      setError(null);
      setChartData([]); // Clear previous data

      try {
        // 1. Get user session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !session?.user) {
          throw new Error(sessionError?.message || "User not authenticated.");
        }
        const userId = session.user.id;

        // 2. Fetch only the 'language' column for the user's entries
        const { data: entries, error: fetchError } = await supabase
          .from("entries") // Ensure 'entries' matches your table name
          .select("language") // Only fetch the necessary column
          .eq("user_id", userId); // *** CRITICAL: Filter by user ID ***

        if (fetchError) {
          throw fetchError; // Propagate fetch error
        }

        // Check if entries data is available and not empty
        if (!entries || entries.length === 0) {
          // No entries found for the user, set empty data and stop loading
          setChartData([]);
          setIsLoading(false);
          return;
        }

        // 3. Aggregate counts on the client-side
        // Note: For very large numbers of entries, consider doing this aggregation in the database
        const languageCounts = entries.reduce((acc, entry) => {
          const lang = entry.language || "Unknown"; // Handle potential null/empty language values
          acc[lang] = (acc[lang] || 0) + 1;
          return acc;
        }, {}); // Initialize accumulator as an empty object

        // 4. Format data for Recharts PieChart: [{ name: 'Language', value: count }, ...]
        const formattedData = Object.entries(languageCounts).map(([name, value]) => ({
          // Capitalize language name for display
          name: name.charAt(0).toUpperCase() + name.slice(1),
          value,
        }));

        // 5. Sort data (e.g., by count descending for visual hierarchy)
        formattedData.sort((a, b) => b.value - a.value);

        // 6. Update state
        setChartData(formattedData);

      } catch (err) {
        console.error("Error fetching language distribution:", err);
        setError(err.message || "Failed to load language data.");
        setChartData([]); // Ensure data is empty on error
      } finally {
        setIsLoading(false); // Finish loading
      }
    }

    fetchLanguageDistribution();
    // Add supabase dependency
  }, [supabase]);

  // --- Render Loading State ---
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Language Distribution</CardTitle>
          <CardDescription>Analyzing your entry languages...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center items-center min-h-[300px]">
          {/* Use a skeleton matching the chart area */}
          <Skeleton className="h-[250px] w-[250px] rounded-full" />
        </CardContent>
      </Card>
    );
  }

  // --- Render Error State ---
  if (error) {
     return (
      <Card>
        <CardHeader>
          <CardTitle>Language Distribution</CardTitle>
           <CardDescription>Could not load data.</CardDescription>
        </CardHeader>
         <CardContent className="flex justify-center items-center min-h-[300px]">
          <p className="text-destructive text-center">{error}</p>
        </CardContent>
      </Card>
    );
  }


  // --- Render Empty State (No entries found) ---
  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Language Distribution</CardTitle>
          <CardDescription>Share of entries per language.</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center items-center min-h-[300px]">
          <p className="text-muted-foreground text-center">
            Write some journal entries to see your language distribution here.
          </p>
        </CardContent>
      </Card>
    );
  }

  // --- Render Pie Chart ---
  return (
    <Card>
      <CardHeader>
        <CardTitle>Language Distribution</CardTitle>
        <CardDescription>Share of entries per language.</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Set a fixed height for the chart container */}
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              {/* Configure the Pie segment */}
              <Pie
                data={chartData} // The processed data array
                dataKey="value" // Key in data objects containing the numerical value
                nameKey="name" // Key in data objects containing the label/name
                cx="50%" // Center X coordinate
                cy="50%" // Center Y coordinate
                outerRadius={100} // Size of the pie chart
                fill="#8884d8" // Default fill (overridden by Cells)
                labelLine={false} // Disable connecting lines for labels
                // Optional: Add labels directly on slices (can get crowded)
                // label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {/* Map data points to Cell components to assign specific colors */}
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              {/* Tooltip shows details on hover */}
              <Tooltip formatter={(value, name) => [`${value} entries`, name]} />
              {/* Legend displays language names */}
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}