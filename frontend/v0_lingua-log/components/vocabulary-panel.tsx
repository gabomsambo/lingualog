"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { BookOpen, Plus, Check, Volume2, Info } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface VocabularyWord {
  id: string
  word: string
  reading?: string
  romaji?: string
  partOfSpeech: string
  definition: string
  example: string
  level: string
  saved: boolean
}

interface VocabularyPanelProps {
  vocabulary: VocabularyWord[]
  language: string
  onSaveWord: (id: string) => void
}

export function VocabularyPanel({ vocabulary, language, onSaveWord }: VocabularyPanelProps) {
  const [filter, setFilter] = useState("all")

  // Filter vocabulary based on selected filter
  const filteredVocabulary =
    filter === "all"
      ? vocabulary
      : filter === "saved"
        ? vocabulary.filter((word) => word.saved)
        : vocabulary.filter((word) => !word.saved)

  // Get level badge color
  const getLevelBadgeColor = (level: string) => {
    switch (level) {
      case "beginner":
        return "blue"
      case "intermediate":
        return "purple"
      case "advanced":
        return "pink"
      default:
        return "default"
    }
  }

  // Simulate playing pronunciation
  const playPronunciation = (word: string) => {
    console.log(`Playing pronunciation for: ${word}`)
    // In a real app, this would trigger audio playback
  }

  return (
    <Card className="border-fun-yellow/20 shadow-fun rounded-3xl overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-fun-yellow/10 to-fun-orange/10 pb-4">
        <div className="flex justify-between items-center">
          <CardTitle className="text-2xl">
            <span className="fun-heading">New Words from This Entry</span> 📚
          </CardTitle>

          <Tabs defaultValue="all" value={filter} onValueChange={setFilter}>
            <TabsList className="bg-fun-yellow/10 p-1 rounded-full">
              <TabsTrigger
                value="all"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-primary"
              >
                All Words
              </TabsTrigger>
              <TabsTrigger
                value="saved"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-primary"
              >
                Saved
              </TabsTrigger>
              <TabsTrigger
                value="new"
                className="rounded-full data-[state=active]:bg-white data-[state=active]:text-primary"
              >
                New
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        {filteredVocabulary.length === 0 ? (
          <div className="text-center py-8">
            <BookOpen className="h-12 w-12 text-fun-yellow mx-auto mb-4" />
            <h3 className="text-xl font-medium mb-2">No words found</h3>
            <p className="text-muted-foreground">
              {filter === "saved"
                ? "You haven't saved any words from this entry yet."
                : filter === "new"
                  ? "All words from this entry have been saved."
                  : "No vocabulary words were extracted from this entry."}
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {filteredVocabulary.map((word, index) => (
              <motion.div
                key={word.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Card className="border-fun-yellow/20 hover:border-fun-yellow/40 transition-colors duration-300 rounded-2xl shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="text-lg font-bold flex items-center">
                          {word.word}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => playPronunciation(word.word)}
                            className="ml-1 h-6 w-6 p-0 rounded-full hover:bg-fun-blue/10"
                          >
                            <Volume2 className="h-3.5 w-3.5 text-fun-blue" />
                            <span className="sr-only">Pronunciation</span>
                          </Button>
                        </h3>

                        {(word.reading || word.romaji) && (
                          <div className="text-sm text-muted-foreground">
                            {word.reading && <span className="mr-2">{word.reading}</span>}
                            {word.romaji && <span className="italic">{word.romaji}</span>}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        <Badge variant={getLevelBadgeColor(word.level)}>{word.level}</Badge>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSaveWord(word.id)}
                          className={`h-8 w-8 p-0 rounded-full ${
                            word.saved
                              ? "bg-fun-green/10 hover:bg-fun-green/20 text-fun-green"
                              : "hover:bg-fun-yellow/10"
                          }`}
                        >
                          {word.saved ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                          <span className="sr-only">{word.saved ? "Remove from word bank" : "Add to word bank"}</span>
                        </Button>
                      </div>
                    </div>

                    <div className="flex items-center text-sm text-muted-foreground mb-2">
                      <span className="italic">{word.partOfSpeech}</span>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 rounded-full hover:bg-muted ml-1">
                              <Info className="h-3.5 w-3.5 text-muted-foreground" />
                              <span className="sr-only">Part of speech info</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Part of speech in {language}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>

                    <div className="mb-3">
                      <div className="text-sm font-medium">Definition:</div>
                      <div className="text-sm">{word.definition}</div>
                    </div>

                    <div>
                      <div className="text-sm font-medium">Example:</div>
                      <div className="text-sm italic bg-muted/30 p-2 rounded-lg mt-1 font-serif">{word.example}</div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
