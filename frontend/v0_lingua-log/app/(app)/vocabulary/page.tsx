"use client"

import { useState, useEffect, useMemo } from "react"
import { motion } from "framer-motion"
import { Trash2, Search, Filter, X, Info, BookOpen, Languages } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/components/ui/use-toast"
import { LoadingSpinner } from "@/components/loading-spinner"
import { getVocabularyItems, deleteVocabularyItem, UserVocabularyItemResponse } from "@/lib/api"
import { getLanguageEmoji } from "@/lib/utils"
import Link from "next/link"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import LearnWordModal, { VocabWordData } from "@/components/LearnWordModal"

export default function VocabularyPage() {
  const { toast } = useToast()
  const [allVocab, setAllVocab] = useState<UserVocabularyItemResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [languageFilter, setLanguageFilter] = useState("all")

  const [isLearnModalOpen, setIsLearnModalOpen] = useState(false)
  const [selectedVocabForModal, setSelectedVocabForModal] = useState<VocabWordData | null>(null)

  const fetchVocab = async () => {
    setIsLoading(true)
    try {
      const items = await getVocabularyItems()
      setAllVocab(items || [])
    } catch (error: any) {
      toast({ title: "Error fetching vocabulary", description: error.message, variant: "destructive" })
      setAllVocab([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchVocab()
  }, [])

  const handleDeleteVocabItem = async (itemId: string, term: string) => {
    // Optimistic UI update can be added here if desired
    try {
      await deleteVocabularyItem(itemId)
      toast({ title: "Vocabulary Item Deleted", description: `"${term}" removed from your vocabulary.` })
      setAllVocab(prev => prev.filter(item => item.id !== itemId))
    } catch (error: any) {
      toast({ title: "Error deleting item", description: error.message, variant: "destructive" })
    }
  }

  const availableLanguages = useMemo(() => {
    const languages = new Set(allVocab.map(item => item.language))
    return [{ value: "all", label: "All Languages" }, ...Array.from(languages).sort().map(lang => ({ value: lang, label: lang }))]
  }, [allVocab])

  const filteredVocab = useMemo(() => {
    return allVocab.filter(item => {
      const matchesLang = languageFilter === "all" || item.language === languageFilter
      const matchesSearch = searchTerm === "" || 
                            item.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            (item.definition && item.definition.toLowerCase().includes(searchTerm.toLowerCase())) ||
                            (item.example_sentence && item.example_sentence.toLowerCase().includes(searchTerm.toLowerCase()))
      return matchesLang && matchesSearch
    }).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) // Sort by newest first
  }, [allVocab, searchTerm, languageFilter])

  const handleOpenLearnModal = (item: UserVocabularyItemResponse) => {
    // Construct vocabModalData with ALL fields from the enriched vocabulary item
    const vocabModalData: Partial<VocabWordData> = {
      id: item.id,
      word: item.term,
      term: item.term, // Include both for compatibility
      romaji: item.reading || "",
      language: item.language,
      definition: item.definition,
      exampleSentence: item.example_sentence,
      example_sentence: item.example_sentence,
      partOfSpeech: item.part_of_speech,
      part_of_speech: item.part_of_speech,
      frequency: ['Common', 'Uncommon', 'Rare'].includes(item.status || '') 
                   ? item.status as VocabWordData['frequency'] 
                   : undefined,
      
      // AI Enrichment fields - pass ALL enriched data to modal
      ai_example_sentences: item.ai_example_sentences,
      ai_definitions: item.ai_definitions,
      ai_synonyms: item.ai_synonyms,
      ai_antonyms: item.ai_antonyms,
      ai_related_phrases: item.ai_related_phrases,
      ai_conjugation_info: item.ai_conjugation_info,
      ai_cultural_note: item.ai_cultural_note,
      ai_pronunciation_guide: item.ai_pronunciation_guide,
      ai_alternative_forms: item.ai_alternative_forms,
      ai_common_mistakes: item.ai_common_mistakes,
      ai_eli5_explanation: item.ai_eli5_explanation,
      emotion_tone: item.emotion_tone,
      mnemonic: item.mnemonic,
      emoji: item.emoji,
      source_model: item.source_model,
      notes_user: item.notes_user,
      tags: item.tags,
    };

    // Explicitly remove keys that are undefined, so they don\'t overwrite placeholders with undefined
    const cleanedVocabModalData = Object.fromEntries(
      Object.entries(vocabModalData).filter(([_, v]) => v !== undefined)
    ) as Partial<VocabWordData>;

    setSelectedVocabForModal(cleanedVocabModalData as VocabWordData); // Cast needed due to Partial, modal handles defaults
    setIsLearnModalOpen(true);
  };

  const handleCloseLearnModal = () => {
    setIsLearnModalOpen(false);
    setSelectedVocabForModal(null);
  };

  const WordCard = ({ item }: { item: UserVocabularyItemResponse }) => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card className="h-full flex flex-col fun-card border-fun-purple/20 hover:border-fun-purple/40 transition-all duration-300 hover:shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex justify-between items-start">
            <CardTitle className="text-xl font-bold group-hover:text-fun-purple transition-colors duration-300">
              {item.term}
              {item.reading && <span className="ml-2 text-sm font-normal text-muted-foreground">({item.reading})</span>}
            </CardTitle>
            <Badge variant="outline" className="text-xs">{getLanguageEmoji(item.language)} {item.language}</Badge>
          </div>
          {item.part_of_speech && <p className="text-xs text-muted-foreground capitalize">{item.part_of_speech}</p>}
        </CardHeader>
        <CardContent className="flex-grow space-y-2 text-sm">
          {item.definition && <div><strong>Definition:</strong> {item.definition}</div>}
          {item.example_sentence && (
            <div className="p-2 bg-slate-50 dark:bg-slate-700/50 rounded-md">
                <p className="text-xs italic text-slate-500 dark:text-slate-400">
                    <Info size={12} className="inline mr-1"/> 
                    Example: "{item.example_sentence}"
                </p>
            </div>
          )}
          {item.entry_id && (
            <TooltipProvider delayDuration={100}>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Link href={`/entries/${item.entry_id}`} className="text-xs text-blue-500 hover:underline inline-flex items-center">
                           Source Entry <BookOpen size={12} className="ml-1"/>
                        </Link>
                    </TooltipTrigger>
                    <TooltipContent className="bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-800 rounded-md">
                        <p>View the journal entry where this word was saved.</p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>
            )}
        </CardContent>
        <CardFooter className="pt-2 flex flex-col sm:flex-row gap-2">
            <Button
                variant="outline"
                size="sm"
                className="w-full rounded-md text-blue-600 border-blue-500 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-400 dark:hover:bg-blue-900/50 hover:text-blue-700"
                onClick={() => handleOpenLearnModal(item)}
            >
                <BookOpen className="mr-2 h-4 w-4" /> Learn It
            </Button>
            <Button 
                variant="ghost" 
                size="sm"
                className="w-full text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 hover:text-red-600 rounded-md"
                onClick={() => handleDeleteVocabItem(item.id, item.term)}
            >
                <Trash2 className="mr-2 h-4 w-4" /> Remove
            </Button>
        </CardFooter>
      </Card>
    </motion.div>
  )

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="mb-8">
        <h1 className="text-4xl font-bold mb-2">
            <span className="fun-heading">My Vocabulary</span> 📖
        </h1>
        <p className="text-xl text-muted-foreground">Review and manage all the words you've saved.</p>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }} className="mb-8 p-4 bg-card border rounded-lg shadow-sm">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search term, definition, example..."
              className="pl-10 fun-input h-12 text-base"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <Button variant="ghost" size="icon" className="absolute right-1 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full" onClick={() => setSearchTerm("")}>
                <X className="h-5 w-5" />
              </Button>
            )}
          </div>
          <Select value={languageFilter} onValueChange={setLanguageFilter}>
            <SelectTrigger className="w-full sm:w-[200px] h-12 fun-input text-base">
                <div className="flex items-center">
                    <Languages className="h-5 w-5 mr-2 text-muted-foreground" />
                    <SelectValue placeholder="Filter by language" />
                </div>
            </SelectTrigger>
            <SelectContent className="rounded-xl border-fun-purple/30">
              {availableLanguages.map(lang => (
                <SelectItem key={lang.value} value={lang.value} className="text-base py-2">{lang.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </motion.div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
            <LoadingSpinner text="Loading your vocabulary..." />
        </div>
      ) : filteredVocab.length === 0 ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }} className="text-center py-16">
          <BookOpen className="h-16 w-16 mx-auto mb-6 text-fun-purple opacity-70" />
          <h2 className="text-2xl font-bold mb-3">No Vocabulary Found</h2>
          {allVocab.length > 0 ? (
            <p className="text-muted-foreground text-lg mb-8">Try adjusting your search or language filter.</p>
          ) : (
            <p className="text-muted-foreground text-lg mb-8">Start saving words from your journal entries to build your vocabulary list!</p>
          )}
           <Button asChild size="lg" className="rounded-full bg-gradient-to-r from-fun-purple to-fun-pink mt-4">
            <Link href="/entries/new">Write a New Entry</Link>
          </Button>
        </motion.div>
      ) : (
        <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredVocab.map(item => (
            <WordCard key={item.id} item={item} />
          ))}
        </motion.div>
      )}
      {selectedVocabForModal && (
        <LearnWordModal
          isOpen={isLearnModalOpen}
          onClose={handleCloseLearnModal}
          vocabEntry={selectedVocabForModal}
        />
      )}
    </div>
  )
}
