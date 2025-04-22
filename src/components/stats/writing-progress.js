// src/components/stats/writing-progress.js
"use client"; // Required for client-side hooks and interactions

import { useState, useEffect } from "react";
import { format, subDays, startOfDay } from "date-fns"; // Added startOfDay for accurate date comparison
// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"; // Added CardDescription
import { Skeleton } from "@/components/ui/skeleton"; // Ensure you have this component

// --- Chart Imports ---
// Ensure recharts is installed: npm install recharts
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function WritingProgress() {
  // State variables
  const [chartData, setChartData] = useState([]); // Data formatted for the LineChart
  const [isLoading, setIsLoading] = useState(true); // Loading state
  const [error, setError] = useState(null); // Error state
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client

  // Effect hook to fetch and process writing progress data
  useEffect(() => {
    async function fetchWritingProgress() {
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

        // 2. Define date range (last 30 days)
        const today = startOfDay(new Date()); // Use startOfDay for consistent comparison
        const daysToFetch = 30;
        const dateRange = Array.from({ length: daysToFetch }, (_, i) => {
          // Calculate date for each of the last 30 days
          return subDays(today, i);
        }).reverse(); // Reverse to have the oldest date first

        // Get the ISO string for the start of the period for the Supabase query
        const startDateISO = dateRange[0].toISOString();

        // 3. Fetch entries within the date range for the user
        const { data: entries, error: fetchError } = await supabase
          .from("entries")
          .select("content, created_at") // Select content for word count and created_at for grouping
          .eq("user_id", userId) // Filter by user ID
          .gte("created_at", startDateISO); // Filter entries created on or after the start date

        if (fetchError) {
          throw fetchError; // Propagate fetch error
        }

        // Check if entries data is available
        if (!entries) {
           setChartData([]); // Set empty data if fetch returned null
           setIsLoading(false);
           return;
        }

        // 4. Process data: Group word counts by date
        // Create a map for efficient lookup of word counts per day
        const wordCountMap = entries.reduce((acc, entry) => {
          const entryDateStr = format(startOfDay(new Date(entry.created_at)), "yyyy-MM-dd");
          const words = entry.content?.split(/\s+/).filter(Boolean) || [];
          acc[entryDateStr] = (acc[entryDateStr] || 0) + words.length;
          return acc;
        }, {}); // Initialize accumulator as empty object

        // 5. Format data for Recharts LineChart: [{ date: 'Mon DD', wordCount: count }, ...]
        const formattedData = dateRange.map(date => {
          const dateStr = format(date, "yyyy-MM-dd"); // Key for the map
          return {
            // Format date for X-axis label (e.g., "Apr 22")
            date: format(date, "MMM d"),
            // Get word count from map, default to 0 if no entries on that day
            wordCount: wordCountMap[dateStr] || 0,
          };
        });

        // 6. Update state
        setChartData(formattedData);

      } catch (err) {
        console.error("Error fetching writing progress:", err);
        setError(err.message || "Failed to load writing progress data.");
        setChartData([]); // Ensure data is empty on error
      } finally {
        setIsLoading(false); // Finish loading
      }
    }

    fetchWritingProgress();
    // Add supabase dependency
  }, [supabase]);

  // --- Render Loading State ---
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Writing Progress (Last 30 Days)</CardTitle>
          <CardDescription>Tracking daily word count...</CardDescription>
        </CardHeader>
        <CardContent className="pt-4"> {/* Added padding top */}
          {/* Skeleton matching the chart area */}
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

   // --- Render Error State ---
   if (error) {
     return (
      <Card>
        <CardHeader>
          <CardTitle>Writing Progress (Last 30 Days)</CardTitle>
           <CardDescription>Could not load data.</CardDescription>
        </CardHeader>
         <CardContent className="flex justify-center items-center min-h-[300px]">
          <p className="text-destructive text-center">{error}</p>
        </CardContent>
      </Card>
    );
  }

  // --- Render Line Chart (or Empty State implicitly handled by chart if data is empty) ---
  return (
    <Card>
      <CardHeader>
        <CardTitle>Writing Progress (Last 30 Days)</CardTitle>
        <CardDescription>Word count per day.</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Container with fixed height for the chart */}
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData} // The processed data array
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }} // Adjusted margins
            >
              {/* Grid lines for reference */}
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.5} />
              {/* X-axis configuration (Date) */}
              <XAxis
                dataKey="date" // Key in data objects for x-axis values
                tick={{ fontSize: 10 }} // Smaller font size for ticks
                tickMargin={5} // Space between ticks and axis line
                // Optional: interval='preserveStartEnd' or calculate interval based on data length
                // interval={4} // Show roughly 7 ticks for 30 days
              />
              {/* Y-axis configuration (Word Count) */}
              <YAxis
                 tick={{ fontSize: 10 }}
                 tickMargin={5}
                 // Allow decimal ticks if counts are low, otherwise default is fine
                 // allowDecimals={false}
              />
              {/* Tooltip configuration */}
              <Tooltip
                contentStyle={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px' }}
                formatter={(value, name) => [`${value} words`, name]} // Format tooltip content
                labelFormatter={(label) => `Date: ${label}`} // Format tooltip title (date)
              />
              {/* Line configuration */}
              <Line
                type="monotone" // Smoothing type for the line
                dataKey="wordCount" // Key in data objects for y-axis values (line height)
                name="Words Written" // Name shown in tooltip
                stroke="#16a34a" // Line color (e.g., green)
                strokeWidth={2} // Line thickness
                dot={false} // Hide dots on data points for cleaner look
                activeDot={{ r: 6, strokeWidth: 1, fill: '#16a34a' }} // Style for dot on hover
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}