"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, Star, StarOff, Download, Copy, Check, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/components/ui/use-toast"
import { EntryViewer } from "@/components/entry-viewer"
import { TranslationPanel } from "@/components/translation-panel"
import { GrammarFeedback } from "@/components/grammar-feedback"
import { FluencyScore } from "@/components/fluency-score"
import { VocabularyPanel } from "@/components/vocabulary-panel"
import { LoadingSpinner } from "@/components/loading-spinner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getEntryById, getVocabularyItems, UserVocabularyItemResponse } from "@/lib/api"
import type { Entry, GrammarSuggestion, NewWord, Rubric } from "@/types/entry"

// Helper to determine fluency level based on score
const determineFluencyLevel = (score: number): string => {
  if (score >= 90) return "Advanced";
  if (score >= 75) return "Intermediate";
  if (score >= 50) return "Beginner";
  return "Novice";
};

// Helper to get language emoji (you might want to move this to a utils file)
const getLanguageEmoji = (languageCode?: string): string => {
  if (!languageCode) return "📝";
  switch (languageCode?.toLowerCase()) {
    case "ja": return "🇯🇵";
    case "en": return "🇬🇧";
    case "es": return "🇪🇸";
    case "fr": return "🇫🇷";
    case "de": return "🇩🇪";
    // Add more language codes and their emojis as needed
    default: return "📝";
  }
};

// Helper to map language name to code (you might want to move this to a utils file)
const mapLanguageToCode = (languageName?: string): string => {
  if (!languageName) return "unknown";
  switch (languageName.toLowerCase()) {
    case "japanese": return "ja";
    case "english": return "en";
    case "spanish": return "es";
    case "french": return "fr";
    case "german": return "de";
    // Add more mappings as needed
    default: return "unknown";
  }
};

export default function EntryInsightPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [entry, setEntry] = useState<Entry | null>(null)
  const [showTranslation, setShowTranslation] = useState(false)
  const [isFavorite, setIsFavorite] = useState(false)
  const [copied, setCopied] = useState(false)
  const [userVocabulary, setUserVocabulary] = useState<UserVocabularyItemResponse[]>([])
  const [processedWords, setProcessedWords] = useState<NewWord[]>([])
  const [vocabLoading, setVocabLoading] = useState(true)

  const loadFullEntryData = useCallback(async () => {
    if (!params.id || typeof params.id !== 'string') {
      setLoading(false)
      toast({ title: "Error", description: "Invalid entry ID.", variant: "destructive" })
      router.push("/dashboard")
      return
    }
    setLoading(true)
    setVocabLoading(true)

    try {
      const [fetchedEntryData, fetchedUserVocabulary] = await Promise.all([
        getEntryById(params.id as string),
        getVocabularyItems()
      ])

      setUserVocabulary(fetchedUserVocabulary || [])

      if (fetchedEntryData) {
        // Cast to any to access ai_feedback, as the fetchedEntryData is typed as frontend Entry
        const apiResponse = fetchedEntryData as any; 
        const aiFeedbackData = apiResponse.ai_feedback; // Extract for easier access

        const processedEntry: Entry = {
          // Spread common top-level fields from fetchedEntryData (which is typed as Entry)
          id: fetchedEntryData.id,
          user_id: fetchedEntryData.user_id,
          content: fetchedEntryData.content || "", // Already correct and part of Entry type
          title: fetchedEntryData.title || `Entry from ${new Date(fetchedEntryData.created_at || Date.now()).toLocaleDateString()}`,
          language: fetchedEntryData.language || "Unknown",
          languageCode: mapLanguageToCode(fetchedEntryData.language),
          languageEmoji: getLanguageEmoji(mapLanguageToCode(fetchedEntryData.language)),
          created_at: fetchedEntryData.created_at,
          updated_at: fetchedEntryData.updated_at,
          is_favorite: fetchedEntryData.is_favorite || false,
          tags: (apiResponse.tags as string[] | undefined) || [], // Assuming tags might come from apiResponse top level
          
          // AI Feedback Fields - Mapped from aiFeedbackData
          translation: aiFeedbackData?.translation || "",
          explanation: aiFeedbackData?.explanation || "", 
          rewritten_text: aiFeedbackData?.rewrite || "",   
          score: aiFeedbackData?.score ?? 0,              
          tone: aiFeedbackData?.tone || "Neutral",        
          rubric: aiFeedbackData?.rubric || { grammar: 0, vocabulary: 0, complexity: 0 },
          grammar_suggestions: (aiFeedbackData?.grammar_suggestions || []).map((s: GrammarSuggestion, index: number) => ({
            ...s,
            id: s.id || `g-${index}`,
            dismissed: s.dismissed || false,
          })),
          new_words: (aiFeedbackData?.new_words || []).map((w: NewWord, index: number) => ({ // Added typing for new_words map as well for consistency
            ...w,
            id: w.id || `word-${index}` // Ensure new_words also get a unique id if missing
          })),
        };
        
        const currentWords = (processedEntry.new_words || []).map(word => {
          const savedVersion = (fetchedUserVocabulary || []).find(
            item => item.term === word.term && item.language === processedEntry.language
          )
          return {
            ...word,
            id: word.id || word.term,
            db_id: savedVersion ? savedVersion.id : undefined,
            saved: !!savedVersion,
          }
        })
        setProcessedWords(currentWords)
        setEntry(processedEntry)
        setIsFavorite(processedEntry.is_favorite || false)
      } else {
        toast({ title: "Entry not found", description: "Could not find the requested entry.", variant: "destructive" })
        router.push("/dashboard")
      }
    } catch (error) {
      console.error("Failed to load entry or vocabulary:", error)
      toast({ title: "Error", description: "Failed to load entry details or vocabulary.", variant: "destructive" })
    } finally {
      setLoading(false)
      setVocabLoading(false)
    }
  }, [params.id, toast, router])

  useEffect(() => {
    loadFullEntryData()
  }, [loadFullEntryData])

  const handleVocabularyUpdate = () => {
    loadFullEntryData()
  }

  const handleCopyText = () => {
    if (entry?.content) {
      navigator.clipboard.writeText(entry.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast({ title: "Copied!", description: "Entry text copied to clipboard." })
    }
  }

  const handleExportPDF = () => {
    toast({ title: "Coming Soon!", description: "PDF export will be available in a future update." })
  }

  const handleToggleFavorite = async () => {
    if (!entry) return;
    const newFavoriteStatus = !isFavorite;
    setIsFavorite(newFavoriteStatus);
    toast({
      title: newFavoriteStatus ? "Added to favorites" : "Removed from favorites",
    });
    setEntry(prev => prev ? { ...prev, is_favorite: newFavoriteStatus } : null);
  };

  const handleDismissGrammarFeedback = (id: string) => {
    setEntry(prev => {
      if (!prev || !prev.grammar_suggestions) return prev;
      return {
        ...prev,
        grammar_suggestions: prev.grammar_suggestions.map(item =>
          item.id === id ? { ...item, dismissed: true } : item
        ),
      };
    });
  };

  const handleSaveVocabulary = (id: string) => {
    setEntry(prev => {
      if (!prev || !prev.new_words) return prev;
      const wordToUpdate = prev.new_words.find(word => word.id === id);
      const currentSavedStatus = wordToUpdate ? wordToUpdate.saved : false;
      const newSavedStatus = !currentSavedStatus;

      toast({ title: newSavedStatus ? "Word saved!" : "Word unsaved." });
      return {
        ...prev,
        new_words: prev.new_words.map(item =>
          item.id === id ? { ...item, saved: newSavedStatus } : item
        ),
      };
    });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4">
        <LoadingSpinner />
        <p className="mt-4 text-lg text-muted-foreground">Loading entry insights...</p>
      </div>
    )
  }

  if (!entry) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Button variant="ghost" onClick={() => router.back()} className="mb-6">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="text-center">
          <h2 className="text-2xl font-semibold">Entry Not Found</h2>
          <p className="text-muted-foreground">We couldn\'t find the entry you were looking for.</p>
          <Button onClick={() => router.push("/dashboard")} className="mt-4">
            Go to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  const fluencyScoreData = {
    overall: entry.score || 0,
    level: determineFluencyLevel(entry.score || 0),
    grammar: entry.rubric?.grammar || 0,
    vocabulary: entry.rubric?.vocabulary || 0,
    complexity: entry.rubric?.complexity || 0,
    improvement: entry.explanation || "",
    tone: entry.tone || "Neutral",
  };

  const grammarFeedbackItemsForComponent = (entry.grammar_suggestions || []).filter(item => !item.dismissed)
    .map((suggestion, index) => ({
      ...suggestion,
      id: suggestion.id || `gram-${index}`,
      suggested: suggestion.corrected,
      explanation: suggestion.note,
      type: "suggestion" as "suggestion" | "positive" | "error",
      dismissed: suggestion.dismissed || false,
    }));

  const vocabularyItems = entry.new_words || [];

  const vocabularyItemsForPanel = vocabularyItems.map(nw => ({
    id: nw.id || String(Math.random()),
    word: nw.term,
    reading: nw.reading || undefined,
    romaji: undefined,
    partOfSpeech: nw.pos,
    definition: nw.definition,
    example: nw.example || "",
    level: nw.proficiency || "unknown",
    saved: nw.saved || false,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="container mx-auto max-w-4xl px-4 py-8"
    >
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <Button variant="ghost" onClick={() => router.back()} className="flex items-center text-sm text-muted-foreground hover:text-primary">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Entries
        </Button>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={handleCopyText}>
            {copied ? <Check className="mr-2 h-4 w-4 text-green-500" /> : <Copy className="mr-2 h-4 w-4" />}
            {copied ? "Copied!" : "Copy Text"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportPDF}>
            <Download className="mr-2 h-4 w-4" />
            Export PDF
          </Button>
          <Button variant="outline" size="icon" onClick={handleToggleFavorite} title={entry.is_favorite ? "Remove from favorites" : "Add to favorites"}>
            {entry.is_favorite ? <StarOff className="h-5 w-5 text-yellow-500 fill-yellow-500" /> : <Star className="h-5 w-5 text-muted-foreground" />}
          </Button>
        </div>
      </div>

      <div className="mb-8 p-6 bg-card border rounded-lg shadow">
        <h1 className="text-3xl font-bold mb-2 text-primary">{entry.title}</h1>
        <div className="flex items-center text-sm text-muted-foreground">
          <span className="mr-1">{entry.languageEmoji}</span>
          <span>{entry.language}</span>
          <span className="mx-2">·</span>
          <span>Written on {new Date(entry.created_at || Date.now()).toLocaleDateString("en-US", { year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>
      
      {/* ROW 1: Entry Viewer (Full Width) */}
      <div className="mb-8">
        <EntryViewer entry={{
          title: entry.title || "Entry",
          language: entry.language || "Unknown",
          languageEmoji: entry.languageEmoji || "📝",
          date: entry.created_at || new Date().toISOString(),
          content: entry.content
        }} />
      </div>

      {/* ROW 2: Translation Panel (Full Width) */}
      <div className="mb-8">
        <TranslationPanel entry={{
            language: entry.language || "Unknown",
            content: entry.content,
            translation: entry.translation
          }}
          showTranslation={showTranslation}
          setShowTranslation={setShowTranslation} />
      </div>

      {/* ROW 3: Fluency Score (1/2) & Summary/Notes (1/2) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="space-y-8"> {/* Allow stacking if other items were here */}
          <FluencyScore score={fluencyScoreData} />
        </div>
        <div className="space-y-8">
          {entry.explanation && entry.explanation.trim() !== "" && (
            <Card className="border-fun-gray/20 shadow-fun rounded-3xl overflow-hidden">
              <CardHeader className="bg-gradient-to-r from-fun-gray/10 to-fun-blue/5 pb-3">
                <CardTitle className="text-xl fun-heading">Summary & Notes</CardTitle>
              </CardHeader>
              <CardContent className="p-4 text-sm text-muted-foreground prose max-w-none">
                {entry.explanation.split('\\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* ROW 4: Grammar Suggestions (Full Width) */}
      <div className="mb-8">
        <GrammarFeedback
          feedback={grammarFeedbackItemsForComponent}
          onDismiss={handleDismissGrammarFeedback}
        />
      </div>

      {/* ROW 5: Vocabulary Panel (Full Width) */}
      <div className="mb-8">
        <VocabularyPanel
          words={processedWords}
          language={entry.language || "Unknown"}
          entryId={entry.id}
          onVocabularyUpdate={handleVocabularyUpdate}
          isLoading={vocabLoading}
        />
      </div>

    </motion.div>
  )
}
