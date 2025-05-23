"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Search, Filter, X, Languages, Plus, BookOpen, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LoadingSpinner } from "@/components/loading-spinner"
import { EntryCard } from "@/components/entry-card"
import { getEntries } from "@/lib/api"
import { formatDate } from "@/lib/utils"
import type { Entry } from "@/types/entry"

// We'll use tone options since we don't have language in the new Entry type
const toneOptions = [
  { value: "all", label: "All Tones" },
  { value: "Reflective", label: "💭 Reflective" },
  { value: "Confident", label: "💪 Confident" },
  { value: "Neutral", label: "⚖️ Neutral" },
]

// Badge variants for tones
const toneBadgeVariants: Record<string, "blue" | "green" | "default" | "outline" | "pink" | "purple" | "yellow"> = {
  Reflective: "blue",
  Confident: "green",
  Neutral: "default",
}

export default function EntriesPage() {
  const [loading, setLoading] = useState(true)
  const [entries, setEntries] = useState<Entry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [toneFilter, setToneFilter] = useState("all")

  useEffect(() => {
    async function fetchEntries() {
      try {
        setLoading(true)
        
        const data = await getEntries()
        
        setEntries(data)
        setError(null)
      } catch (error: any) {
        console.error("Error fetching entries:", error)
        setError(`Failed to load entries. ${error?.toString() || 'Unknown error'}`)
      } finally {
        setLoading(false)
      }
    }

    fetchEntries()
  }, [])

  // Filter entries based on search term and tone filter
  const filteredEntries = entries.filter((entry) => {
    const matchesSearch =
      searchTerm === "" ||
      entry.original_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.translation.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesTone = toneFilter === "all" || entry.tone === toneFilter

    return matchesSearch && matchesTone
  })

  // Function to get a truncated excerpt from the original text
  const getExcerpt = (text: string, maxLength = 150) => {
    if (!text || text.length === 0) return "No content available."; // Handle empty/null text
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + "...";
  };

  // Function to get a display title
  const getDisplayTitle = (title: string | null | undefined, originalText: string) => {
    if (title && title.trim() !== "") {
      return title;
    }
    if (originalText && originalText.trim() !== "") {
      // Fallback: first 5 words of original_text or a generic title
      const words = originalText.trim().split(/\\s+/);
      if (words.length > 0) {
        return words.slice(0, 5).join(" ") + (words.length > 5 ? "..." : "");
      }
    }
    return "Untitled Entry"; // Absolute fallback
  };
  
  const getLanguageEmoji = (language?: string | null): string => {
    if (!language) return "📝"; // Default emoji
    switch (language.toLowerCase()) {
      case "english": return "🇬🇧";
      case "spanish": return "🇪🇸";
      case "french": return "🇫🇷";
      case "german": return "🇩🇪";
      case "japanese": return "🇯🇵";
      // Add more languages and their emojis as needed
      default: return "📝";
    }
  };

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <h1 className="text-4xl font-bold mb-2">
          <span className="fun-heading">Your Journal Entries</span> 📚
        </h1>
        <p className="text-xl text-muted-foreground">View everything you've written and track your growth.</p>
      </motion.div>

      {/* Search and Filter Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="mb-8"
      >
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-4 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Filter by content or translation..."
              className="pl-12 fun-input h-14 text-base"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-2 top-2 h-10 w-10 hover:bg-fun-pink/10 rounded-full"
                onClick={() => setSearchTerm("")}
              >
                <X className="h-5 w-5" />
                <span className="sr-only">Clear search</span>
              </Button>
            )}
          </div>

          <div className="w-full sm:w-64">
            <Select value={toneFilter} onValueChange={setToneFilter}>
              <SelectTrigger className="h-14 fun-input text-base">
                <div className="flex items-center">
                  <Filter className="h-5 w-5 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Filter by tone" />
                </div>
              </SelectTrigger>
              <SelectContent className="rounded-xl border-fun-purple/30">
                {toneOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value} className="text-base py-3">
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </motion.div>

      {/* Entries List */}
      <div className="space-y-6">
        {loading ? (
          // Loading state
          <>
            {[...Array(4)].map((_, i) => (
              <div key={i} className="fun-card border-fun-purple/20 p-6 space-y-4">
                <div className="flex justify-between items-start mb-4">
                  <Skeleton className="h-8 w-64" />
                  <Skeleton className="h-6 w-24" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-3/4" />
                </div>
                <div className="pt-4">
                  <Skeleton className="h-10 w-32" />
                </div>
              </div>
            ))}

            <div className="flex justify-center py-8">
              <LoadingSpinner text="Loading your entries..." />
            </div>
          </>
        ) : error ? (
          // Error state
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="text-center py-16"
          >
            <X className="h-16 w-16 mx-auto mb-6 text-red-500 opacity-70" />
            <h2 className="text-2xl font-bold mb-3">Something went wrong</h2>
            <p className="text-muted-foreground text-lg mb-8">{error}</p>
            <Button
              variant="outline"
              size="lg"
              className="rounded-full border-fun-purple/30 hover:bg-fun-purple/10"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="mr-2 h-5 w-5" />
              Try Again
            </Button>
          </motion.div>
        ) : filteredEntries.length === 0 ? (
          // Empty state
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="text-center py-16"
          >
            {entries.length === 0 ? (
              // No entries at all
              <>
                <Languages className="h-16 w-16 mx-auto mb-6 text-fun-purple opacity-70" />
                <h2 className="text-2xl font-bold mb-3">No entries yet</h2>
                <p className="text-muted-foreground text-lg mb-8">Start writing to begin your language journey! ✍️</p>
                <Button asChild size="lg" className="rounded-full bg-gradient-to-r from-fun-purple to-fun-pink">
                  <Link href="/entries/new">
                    <Plus className="mr-2 h-5 w-5" />
                    Create First Entry
                  </Link>
                </Button>
              </>
            ) : (
              // No entries matching filters
              <>
                <Search className="h-16 w-16 mx-auto mb-6 text-fun-purple opacity-70" />
                <h2 className="text-2xl font-bold mb-3">No matching entries</h2>
                <p className="text-muted-foreground text-lg mb-8">
                  Try adjusting your search or tone filter to find what you're looking for.
                </p>
                <Button
                  variant="outline"
                  size="lg"
                  className="rounded-full border-fun-purple/30 hover:bg-fun-purple/10"
                  onClick={() => {
                    setSearchTerm("")
                    setToneFilter("all")
                  }}
                >
                  <X className="mr-2 h-5 w-5" />
                  Clear Filters
                </Button>
              </>
            )}
          </motion.div>
        ) : (
          // Entries List - Changed from grid to a single column list
          <div className="space-y-6">
            {filteredEntries
              .filter(entry => !!entry.id) // Ensure entry.id is present and truthy
              .map((entry) => (
              <div key={entry.id!} className="w-full">
                <EntryCard
                  entry={{
                    id: entry.id!, // Assert id is non-null
                    title: getDisplayTitle(entry.title, entry.original_text),
                    language: entry.language || "Unknown", 
                    languageEmoji: getLanguageEmoji(entry.language),
                    date: entry.created_at, 
                    excerpt: getExcerpt(entry.original_text), 
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination (for future implementation) */}
      {!loading && filteredEntries.length > 0 && (
        <div className="mt-10 flex justify-center">
          <p className="text-sm text-muted-foreground">
            Showing {filteredEntries.length} of {entries.length} entries
          </p>
        </div>
      )}
    </div>
  )
}
