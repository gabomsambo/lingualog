"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { BookOpen, Search, X, Lightbulb } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { WritingAnimation } from "@/components/writing-animation"

// Badge variants for languages
const languageBadgeVariants: Record<string, "pink" | "blue" | "purple" | "green" | "yellow" | "default" | "outline"> = {
  Spanish: "pink",
  French: "blue",
  German: "purple",
  Japanese: "green",
  English: "yellow",
  Other: "default",
}

// Mock vocabulary data
const mockVocabulary = [
  {
    id: "1",
    word: "comenzar",
    language: "Spanish",
    translation: "to begin",
    entryId: "1",
    entryTitle: "My first day learning Spanish",
    context: "Estoy muy emocionado por comenzar este viaje.",
  },
  {
    id: "2",
    word: "emocionado",
    language: "Spanish",
    translation: "excited",
    entryId: "1",
    entryTitle: "My first day learning Spanish",
    context: "Estoy muy emocionado por comenzar este viaje.",
  },
  {
    id: "3",
    word: "viaje",
    language: "Spanish",
    translation: "journey, trip",
    entryId: "1",
    entryTitle: "My first day learning Spanish",
    context: "Estoy muy emocionado por comenzar este viaje.",
  },
  {
    id: "4",
    word: "apprendre",
    language: "French",
    translation: "to learn",
    entryId: "2",
    entryTitle: "French vocabulary practice",
    context: "J'aime apprendre le français.",
  },
  {
    id: "5",
    word: "boulangerie",
    language: "French",
    translation: "bakery",
    entryId: "2",
    entryTitle: "French vocabulary practice",
    context: "Je vais à la boulangerie pour acheter du pain.",
  },
  {
    id: "6",
    word: "Bahnhof",
    language: "German",
    translation: "train station",
    entryId: "3",
    entryTitle: "German grammar rules",
    context: "Der Bahnhof ist nicht weit von hier.",
  },
]

export default function VocabularyPage() {
  const [loading, setLoading] = useState(true)
  const [vocabulary, setVocabulary] = useState<typeof mockVocabulary>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [activeLanguage, setActiveLanguage] = useState("all")

  useEffect(() => {
    // Simulate API call
    const timer = setTimeout(() => {
      setVocabulary(mockVocabulary)
      setLoading(false)
    }, 1500)

    return () => clearTimeout(timer)
  }, [])

  // Get unique languages for tabs
  const languages = ["all", ...new Set(mockVocabulary.map((item) => item.language.toLowerCase()))]

  // Filter vocabulary based on search and language
  const filteredVocabulary = vocabulary.filter((item) => {
    const matchesSearch =
      searchTerm === "" ||
      item.word.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.translation.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesLanguage = activeLanguage === "all" || item.language.toLowerCase() === activeLanguage

    return matchesSearch && matchesLanguage
  })

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">
          <span className="fun-heading">Your Vocabulary Collection 📚</span>
        </h2>
        <p className="text-muted-foreground mt-2 text-lg">Track and review vocabulary from your journal entries</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-4 h-5 w-5 text-muted-foreground" />
          <Input
            placeholder="Search words or translations..."
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
      </div>

      <Tabs defaultValue="all" value={activeLanguage} onValueChange={setActiveLanguage}>
        <TabsList className="bg-fun-purple/10 p-1 rounded-full">
          {languages.map((lang) => (
            <TabsTrigger
              key={lang}
              value={lang}
              className="capitalize rounded-full data-[state=active]:bg-white data-[state=active]:text-primary text-base"
            >
              {lang === "all" ? "All Languages" : lang}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="mt-8">
          {loading ? (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[...Array(6)].map((_, i) => (
                <Card key={i} className="fun-card border-fun-purple/20">
                  <CardHeader className="pb-2">
                    <div className="flex justify-between">
                      <Skeleton className="h-8 w-28" />
                      <Skeleton className="h-6 w-20" />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Skeleton className="h-5 w-full" />
                    <Skeleton className="h-5 w-3/4" />
                    <Skeleton className="h-5 w-1/2" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : filteredVocabulary.length === 0 ? (
            <Card className="fun-card border-fun-purple/20">
              <CardContent className="py-12 text-center">
                <Lightbulb className="h-16 w-16 text-fun-yellow mx-auto mb-4" />
                <h3 className="text-xl font-medium">No vocabulary found</h3>
                <p className="text-muted-foreground mt-2 text-lg">
                  {searchTerm
                    ? "Try a different search term or language filter"
                    : "Start writing journal entries to build your vocabulary"}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {filteredVocabulary.map((item) => (
                <Card key={item.id} className="fun-card group border-fun-purple/20 hover:border-fun-purple/40">
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-2xl group-hover:text-fun-purple transition-colors duration-300">
                        {item.word}
                      </CardTitle>
                      <Badge variant={languageBadgeVariants[item.language] || "default"}>{item.language}</Badge>
                    </div>
                    <CardDescription className="font-medium text-fun-purple text-lg">
                      {item.translation}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-base italic text-muted-foreground bg-fun-purple/5 p-4 rounded-2xl border-2 border-fun-purple/10">
                      "{item.context}"
                    </div>
                    <div className="flex items-center text-sm text-muted-foreground">
                      <BookOpen className="h-4 w-4 mr-2 text-fun-pink" />
                      <Link
                        href={`/entries/${item.entryId}`}
                        className="hover:underline hover:text-fun-purple transition-colors duration-200"
                      >
                        From: {item.entryTitle}
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex justify-center py-8">
              <WritingAnimation text="Loading vocabulary" />
            </div>
          )}
        </div>
      </Tabs>
    </div>
  )
}
