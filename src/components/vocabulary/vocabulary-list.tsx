// src/components/vocabulary/vocabulary-list.tsx
"use client";

import { useState, useEffect, useMemo } from "react"; // Added useMemo
// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton"; // Ensure you have this component
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"; // Ensure you have this component
import { Input } from "@/components/ui/input"; // Ensure you have this component

// Define the structure for vocabulary items
type VocabularyItem = {
  id: string;
  word: string;
  language: string;
  // entry_id: string; // Include if needed for linking back
  created_at: string; // Keep as string, format if needed on render
};

// Define language options for the filter dropdown
// Consider moving this to a shared constants file if used elsewhere
const languageOptions = [
  { value: "all", label: "All Languages" },
  { value: "arabic", label: "Arabic" },
  { value: "chinese", label: "Chinese" },
  { value: "english", label: "English" },
  { value: "french", label: "French" },
  { value: "german", label: "German" },
  { value: "italian", label: "Italian" },
  { value: "japanese", label: "Japanese" },
  { value: "korean", label: "Korean" },
  { value: "portuguese", label: "Portuguese" },
  { value: "russian", label: "Russian" },
  { value: "spanish", label: "Spanish" },
  { value: "other", label: "Other" },
];

export function VocabularyList() {
  // State variables
  const [allVocabulary, setAllVocabulary] = useState<VocabularyItem[]>([]); // Stores all fetched vocab
  const [isLoading, setIsLoading] = useState(true); // Loading state
  const [error, setError] = useState<string | null>(null); // Error state
  const [selectedLanguage, setSelectedLanguage] = useState("all"); // Language filter state
  const [searchTerm, setSearchTerm] = useState(""); // Search term state
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client

  // Effect hook to fetch vocabulary data based on the selected language
  useEffect(() => {
    async function fetchVocabulary() {
      setIsLoading(true);
      setError(null);

      try {
        // 1. Get user session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !session?.user) {
          throw new Error(sessionError?.message || "User not authenticated.");
        }
        const userId = session.user.id;

        // 2. Build Supabase query
        let query = supabase
          .from("vocabulary") // Ensure 'vocabulary' matches your table name
          .select('id, word, language, created_at') // Select only needed columns
          .eq('user_id', userId); // *** CRITICAL: Filter by user ID ***

        // 3. Add language filter if not 'all'
        if (selectedLanguage !== "all") {
          query = query.eq("language", selectedLanguage);
        }

        // 4. Add ordering (e.g., by word alphabetically)
        query = query.order("word", { ascending: true }); // Order alphabetically by word

        // 5. Execute the query
        const { data, error: fetchError } = await query;

        if (fetchError) {
          throw fetchError; // Propagate fetch error
        }

        // 6. Update state
        setAllVocabulary(data || []);

      } catch (err: any) {
        console.error("Error fetching vocabulary:", err);
        setError(err.message || "Failed to fetch vocabulary.");
        setAllVocabulary([]); // Clear data on error
      } finally {
        setIsLoading(false); // Finish loading
      }
    }

    fetchVocabulary();
    // Re-run effect when the selected language or supabase client instance changes
  }, [selectedLanguage, supabase]);

  // --- Client-Side Filtering ---
  // Use useMemo to avoid re-calculating on every render unless dependencies change
  const filteredVocabulary = useMemo(() => {
    // Start with all fetched vocabulary (for the selected language)
    let vocabToFilter = allVocabulary;

    // Apply search term filter (case-insensitive)
    if (searchTerm.trim()) { // Only filter if search term is not empty
      vocabToFilter = vocabToFilter.filter(item =>
        item.word.toLowerCase().includes(searchTerm.toLowerCase().trim())
      );
    }

    // Note: If vocabulary list grows large, consider implementing search/filter server-side
    // using Supabase query functions like .ilike() or textSearch() for better performance.

    return vocabToFilter;
  }, [allVocabulary, searchTerm]); // Re-filter only when fetched data or search term changes


  // --- Render Loading State ---
  if (isLoading) {
    return (
      <div>
        {/* Skeleton for filter/search controls */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-4 sm:space-y-0 sm:space-x-0 sm:space-x-4 mb-6">
          <Skeleton className="h-10 w-full sm:w-[180px]" />
          <Skeleton className="h-10 w-full" />
        </div>
        {/* Skeleton for vocabulary cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"> {/* Adjusted columns */}
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={`skeleton-${i}`}>
              <CardHeader className="pb-2">
                <Skeleton className="h-6 w-3/4" /> {/* Skeleton for word */}
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-1/2" /> {/* Skeleton for language */}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // --- Render Error State ---
   if (error) {
    return (
      <div className="rounded-md border border-destructive bg-destructive/10 p-4 text-center text-destructive">
        <p>Error loading vocabulary:</p>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  // --- Render Vocabulary List (or Empty States) ---
  return (
    <div>
      {/* Filter and Search Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-4 sm:space-y-0 sm:space-x-0 sm:space-x-4 mb-6">
        {/* Language Filter Dropdown */}
        <Select
          value={selectedLanguage} // Controlled component value
          onValueChange={(value) => setSelectedLanguage(value || "all")} // Update state on change
        >
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Filter by language" />
          </SelectTrigger>
          <SelectContent>
            {languageOptions.map(option => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Search Input */}
        <Input
          placeholder="Search your vocabulary..."
          value={searchTerm} // Controlled component value
          onChange={(e) => setSearchTerm(e.target.value)} // Update state on change
          className="w-full" // Take remaining width
        />
      </div>

      {/* Conditional Rendering based on fetched and filtered data */}
      {allVocabulary.length === 0 && !isLoading ? (
          // Initial Empty State (no vocab fetched for the user/language)
         <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center mt-8">
           <h3 className="text-lg font-semibold">No Vocabulary Words Found</h3>
           <p className="mt-2 text-sm text-muted-foreground">
             {selectedLanguage === 'all'
               ? "Vocabulary you save from entries will appear here."
               : `You haven't saved any vocabulary for ${languageOptions.find(l => l.value === selectedLanguage)?.label || selectedLanguage} yet.`}
           </p>
         </div>
      ) : filteredVocabulary.length === 0 ? (
          // Filtered Empty State (vocab exists, but none match search)
         <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center mt-8">
           <h3 className="text-lg font-semibold">No Matching Words</h3>
           <p className="mt-2 text-sm text-muted-foreground">
             Try adjusting your search term or language filter.
           </p>
         </div>
      ) : (
          // Vocabulary Grid
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"> {/* Responsive columns */}
            {filteredVocabulary.map((item) => (
              <Card key={item.id} className="overflow-hidden">
                <CardHeader className="pb-2 pt-4"> {/* Adjusted padding */}
                  <CardTitle className="text-lg">{item.word}</CardTitle>
                </CardHeader>
                <CardContent className="pb-4"> {/* Added padding bottom */}
                  {/* Capitalize language name */}
                  <p className="text-sm text-muted-foreground capitalize">
                    {item.language}
                  </p>
                   {/* Optional: Add link back to entry or definition */}
                </CardContent>
              </Card>
            ))}
          </div>
      )}
    </div>
  );
}