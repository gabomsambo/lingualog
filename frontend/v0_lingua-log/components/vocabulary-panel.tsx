"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { BookOpen, Plus, Check, Volume2, Info, PlusCircle, CheckCircle2, HelpCircle, Star } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/components/ui/use-toast"
import type { NewWord as VocabularyWord } from "@/types/entry"
import { addVocabularyItem, deleteVocabularyItem, UserVocabularyItemCreate } from "@/lib/api"

interface VocabularyPanelProps {
  words: VocabularyWord[]
  language: string
  entryId?: string
  onVocabularyUpdate: () => void
  isLoading?: boolean
}

// Define the possible tab states
type VocabTabState = "all" | "new" | "saved"

export function VocabularyPanel({ words, language, entryId, onVocabularyUpdate, isLoading }: VocabularyPanelProps) {
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState<VocabTabState>("all")

  const newWords = words.filter(word => !word.saved)
  const savedWords = words.filter(word => word.saved)
  // allWords is just the words prop directly

  const handleToggleSaveWord = async (word: VocabularyWord) => {
    if (word.saved) {
      if (!word.db_id) {
        toast({ title: "Error", description: "Cannot unsave word: missing database ID.", variant: "destructive" })
        return
      }
      try {
        await deleteVocabularyItem(word.db_id)
        toast({ title: "Word Unsaved", description: `"${word.term}" removed from your vocabulary.`, variant: "default" })
        onVocabularyUpdate()
      } catch (error: any) {
        toast({ title: "Error Unsaving Word", description: error.message || "Could not remove word.", variant: "destructive" })
      }
    } else {
      const vocabItem: UserVocabularyItemCreate = {
        term: word.term,
        language: language,
        part_of_speech: word.pos,
        definition: word.definition,
        reading: word.reading,
        example_sentence: word.example,
        entry_id: entryId,
        status: "saved",
      }
      try {
        // addVocabularyItem will create the item. The parent will refresh the list.
        await addVocabularyItem(vocabItem)
        toast({ title: "Word Saved!", description: `"${word.term}" added to your vocabulary.`, variant: "default" })
        onVocabularyUpdate()
      } catch (error: any) {
        toast({ title: "Error Saving Word", description: error.message || "Could not save word.", variant: "destructive" })
      }
    }
  }

  const renderWordItem = (word: VocabularyWord, index: number) => (
    <motion.div
      key={word.id || word.db_id || word.term}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="border-2 border-yellow-500/20 dark:border-yellow-400/30 rounded-2xl p-4 hover:border-yellow-500/40 dark:hover:border-yellow-400/50 transition-colors duration-300 bg-white dark:bg-slate-800 shadow-sm flex flex-col"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-bold text-purple-600 dark:text-purple-400 flex items-center">
          {word.term}
          {word.reading && <span className="text-sm text-slate-500 dark:text-slate-400 font-normal ml-2">[{word.reading}]</span>}
          <Button variant="ghost" size="icon" className="h-7 w-7 ml-1 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200">
            <Volume2 size={16} />
            <span className="sr-only">Listen to pronunciation (coming soon)</span>
          </Button>
        </h3>
        <TooltipProvider delayDuration={100}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleToggleSaveWord(word)}
                className={`h-8 w-8 p-0 rounded-full ${
                  word.saved 
                    ? 'hover:bg-green-500/10 bg-green-500/10 dark:hover:bg-green-400/20 dark:bg-green-400/20' 
                    : 'hover:bg-yellow-500/10 dark:hover:bg-yellow-400/20'
                }`}
              >
                {word.saved 
                  ? <CheckCircle2 className="h-5 w-5 text-green-500 dark:text-green-400" /> 
                  : <PlusCircle className="h-5 w-5 text-yellow-500 dark:text-yellow-400" />}
                <span className="sr-only">{word.saved ? "Saved to vocabulary" : "Add to vocabulary"}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent className="bg-slate-800 text-white dark:bg-slate-700 dark:text-slate-100 rounded-md text-xs">
              <p>{word.saved ? "Remove from vocabulary" : "Add to vocabulary"}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {word.definition && (
        <div className="text-sm mb-2 text-slate-700 dark:text-slate-300">
          <span className="font-medium text-slate-600 dark:text-slate-400">Definition:</span> {word.definition}
        </div>
      )}

      {word.pos && (
        <div className="text-sm mb-2 text-slate-700 dark:text-slate-300">
          <span className="font-medium text-slate-600 dark:text-slate-400">Part of Speech:</span> <span className="capitalize">{word.pos}</span>
        </div>
      )}
      
      <div className="text-sm mb-2 text-slate-700 dark:text-slate-300">
        <span className="font-medium text-slate-600 dark:text-slate-400">Synonyms:</span> <span className="text-slate-400 dark:text-slate-500 italic">N/A</span>
      </div>

      <div className="text-sm mb-2 text-slate-700 dark:text-slate-300">
        <span className="font-medium text-slate-600 dark:text-slate-400">Antonyms:</span> <span className="text-slate-400 dark:text-slate-500 italic">N/A</span>
      </div>

      <div className="text-sm mb-2 text-slate-700 dark:text-slate-300">
        <span className="font-medium text-slate-600 dark:text-slate-400">Frequency:</span> <span className="text-slate-400 dark:text-slate-500 italic">N/A</span>
      </div>
      
      <div className="text-sm mb-2 text-slate-700 dark:text-slate-300">
        <span className="font-medium text-slate-600 dark:text-slate-400">Cultural Note:</span> <span className="text-slate-400 dark:text-slate-500 italic">N/A</span>
      </div>

      {word.example && (
        <div className="text-sm mt-auto">
          <span className="font-medium text-slate-600 dark:text-slate-400">Example:</span>
          <div className="italic bg-yellow-500/10 dark:bg-yellow-400/10 p-2 rounded-lg mt-1 font-serif text-slate-600 dark:text-slate-300">
            "{word.example}"
          </div>
        </div>
      )}

      <div className="text-sm mt-1 text-slate-700 dark:text-slate-300">
        <span className="font-medium text-slate-600 dark:text-slate-400">Translation:</span> <span className="text-slate-400 dark:text-slate-500 italic">N/A (Example translation coming soon)</span>
      </div>
    </motion.div>
  )

  if (isLoading) {
    return (
      <Card className="shadow-lg rounded-xl overflow-hidden bg-gradient-to-r from-yellow-500/10 via-orange-500/5 to-orange-500/10 dark:from-yellow-600/10 dark:via-orange-600/5 dark:to-orange-600/10 border-yellow-500/20 dark:border-yellow-400/30 shadow-fun rounded-3xl">
        <CardHeader className="pb-4 pt-5 px-5">
          <div className="flex justify-between items-center">
            <CardTitle className="text-xl font-bold text-slate-800 dark:text-slate-100">
                New Words from This Entry 📚
            </CardTitle>
            {/* Slider/Toggle can be placed here if needed */}
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400">Words identified in your journal entry.</p>
           {/* Tabs kept for now, can be restyled or moved */}
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as VocabTabState)} className="mt-3">
            <TabsList className="grid w-full grid-cols-3 bg-slate-200 dark:bg-slate-700 rounded-lg">
              <TabsTrigger value="all" className="rounded-md data-[state=active]:bg-white data-[state=active]:dark:bg-slate-600 data-[state=active]:shadow-sm">All ({words.length})</TabsTrigger>
              <TabsTrigger value="new" className="rounded-md data-[state=active]:bg-white data-[state=active]:dark:bg-slate-600 data-[state=active]:shadow-sm">New ({newWords.length})</TabsTrigger>
              <TabsTrigger value="saved" className="rounded-md data-[state=active]:bg-white data-[state=active]:dark:bg-slate-600 data-[state=active]:shadow-sm">Saved ({savedWords.length})</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="border-2 border-yellow-500/20 dark:border-yellow-400/30 rounded-2xl p-4 bg-white dark:bg-slate-800">
                <div className="flex justify-between items-start mb-2">
                  <Skeleton className="h-6 w-24" />
                  <Skeleton className="h-8 w-8 rounded-full" />
                </div>
                <Skeleton className="h-4 w-20 mb-2" />
                <Skeleton className="h-4 w-full mb-1" />
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-10 w-full rounded-lg" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }
  
  const currentList = activeTab === "new" ? newWords : activeTab === "saved" ? savedWords : words
  const noWordsMessage = activeTab === "new" 
    ? (words.length > 0 && newWords.length === 0 ? "All new words from this entry are already saved!" : "No new words identified in this entry.")
    : activeTab === "saved" 
    ? "No words from this entry are currently saved in your vocabulary."
    : "No words found for the current filter in this entry.";

  return (
    <Card className="shadow-lg rounded-xl overflow-hidden bg-gradient-to-r from-yellow-100/50 via-orange-50/50 to-orange-100/50 dark:from-yellow-700/20 dark:via-orange-700/10 dark:to-orange-700/20 border-yellow-500/30 dark:border-yellow-600/40 shadow-fun rounded-3xl">
      <CardHeader className="pb-4 pt-5 px-5">
        <div className="flex justify-between items-center">
          <CardTitle className="text-xl font-bold text-slate-800 dark:text-slate-100">
            New Words from This Entry 📚
          </CardTitle>
          {/* Tooltip for info can be re-added if needed */}
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-400">Click <PlusCircle size={14} className="inline text-yellow-600 dark:text-yellow-500"/> to save a word, or <CheckCircle2 size={14} className="inline text-green-600 dark:text-green-500"/> if it's already saved.</p>
        {/* Tabs are kept for now for filtering, styling can be adjusted */}
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as VocabTabState)} className="mt-3">
          <TabsList className="grid w-full grid-cols-3 bg-slate-200/80 dark:bg-slate-700/80 rounded-lg backdrop-blur-sm">
            <TabsTrigger value="all" className="rounded-md data-[state=active]:bg-white data-[state=active]:dark:bg-slate-600 data-[state=active]:shadow-sm data-[state=active]:text-yellow-600 dark:data-[state=active]:text-yellow-400">
              All ({words.length})
            </TabsTrigger>
            <TabsTrigger value="new" className="rounded-md data-[state=active]:bg-white data-[state=active]:dark:bg-slate-600 data-[state=active]:shadow-sm data-[state=active]:text-yellow-600 dark:data-[state=active]:text-yellow-400">
              New ({newWords.length})
            </TabsTrigger>
            <TabsTrigger value="saved" className="rounded-md data-[state=active]:bg-white data-[state=active]:dark:bg-slate-600 data-[state=active]:shadow-sm data-[state=active]:text-yellow-600 dark:data-[state=active]:text-yellow-400">
              Saved ({savedWords.length})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent className="p-4"> {/* Adjusted padding */}
        {currentList.length > 0 ? (
          // Removed ScrollArea, grid will handle overflow if page scrolls
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {currentList.map(renderWordItem)}
          </div>
        ) : (
          <p className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">
            {noWordsMessage}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
