"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, Star, StarOff, Download, Copy, Check } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/components/ui/use-toast"
import { EntryViewer } from "@/components/entry-viewer"
import { TranslationPanel } from "@/components/translation-panel"
import { GrammarFeedback } from "@/components/grammar-feedback"
import { FluencyScore } from "@/components/fluency-score"
import { VocabularyPanel } from "@/components/vocabulary-panel"
import { LoadingSpinner } from "@/components/loading-spinner"
import { getEntryById } from "@/lib/api" // Import the API function
import type { Entry } from "@/types/entry" // Import the Entry type

interface GrammarFeedbackItem {
  id: string;
  original: string;
  suggested: string;
  explanation: string;
  type: "positive" | "suggestion" | "error";
  dismissed: boolean;
}

interface VocabularyItem {
  id: string;
  word: string;
  reading: string;
  romaji: string;
  partOfSpeech: string;
  definition: string;
  example: string;
  level: string;
  saved: boolean;
}

interface FluencyScoreData {
  overall: number;
  level: string;
  grammar: number;
  vocabulary: number;
  complexity: number;
  improvement: string;
}

interface MockEntryType {
  id: string;
  title: string;
  language: string;
  languageCode: string;
  languageEmoji: string;
  date: string;
  content: string;
  translation: string;
  isFavorite: boolean;
  fluencyScore: FluencyScoreData;
  grammarFeedback: GrammarFeedbackItem[];
  vocabulary: VocabularyItem[];
}

// Mock entry data (will be partially overridden by fetched data)
const mockEntryData: MockEntryType = {
  id: "1", // Placeholder, will be overridden
  title: "My day at the Japanese restaurant", // Placeholder, will be overridden
  language: "Japanese", // Placeholder, will be overridden
  languageCode: "ja", // Placeholder, can be derived or kept if not in API
  languageEmoji: "🇯🇵", // Placeholder, can be derived or kept if not in API
  date: "2025-04-21T14:30:00Z", // Placeholder
  content: `今日は友達と日本のレストランに行きました。私たちは寿司とラーメンを食べました。とても美味しかったです！

レストランの雰囲気も素晴らしかったです。伝統的な日本の音楽が流れていて、壁には美しい絵が飾られていました。

私は日本語で注文しようとしましたが、少し緊張しました。でも、ウェイターはとても親切で、私の日本語を理解してくれました。彼は「日本語が上手ですね」と言ってくれました。とても嬉しかったです！

次回は、もっと複雑な文章で注文してみたいです。日本語の勉強を続けます！`, // Placeholder, will be overridden
  translation: `Today I went to a Japanese restaurant with my friends. We ate sushi and ramen. It was very delicious!

The atmosphere of the restaurant was also wonderful. Traditional Japanese music was playing, and beautiful pictures were displayed on the walls.

I tried to order in Japanese, but I was a little nervous. However, the waiter was very kind and understood my Japanese. He said "Your Japanese is good!" I was very happy!

Next time, I want to try ordering with more complex sentences. I will continue studying Japanese!`, // Placeholder
  isFavorite: false, // Placeholder
  fluencyScore: { // Placeholder
    overall: 72,
    level: "Intermediate",
    grammar: 80,
    vocabulary: 65,
    complexity: 70,
    improvement: "You're using more varied vocabulary and longer sentences!",
  },
  grammarFeedback: [ // Placeholder
    {
      id: "g1",
      original: "私たちは寿司とラーメンを食べました。",
      suggested: "私たちは寿司とラーメンを食べました。",
      explanation: "This sentence is grammatically correct! Great job using the past tense form correctly.",
      type: "positive",
      dismissed: false,
    },
    {
      id: "g2",
      original: "レストランの雰囲気も素晴らしかったです。",
      suggested: "レストランの雰囲気も素晴らしかったです。",
      explanation: "Perfect use of the past tense adjective form. Well done!",
      type: "positive",
      dismissed: false,
    },
    {
      id: "g3",
      original: "私は日本語で注文しようとしましたが、少し緊張しました。",
      suggested: "私は日本語で注文しようとしましたが、少し緊張しました。",
      explanation: "Excellent use of the 'try to do' form (〜しようとする) and connecting sentences with が.",
      type: "positive",
      dismissed: false,
    },
    {
      id: "g4",
      original: "次回は、もっと複雑な文章で注文してみたいです。",
      suggested: "次回は、もっと複雑な文で注文してみたいです。",
      explanation:
        "Consider using 文 instead of 文章 here. 文 refers to a sentence, while 文章 refers to a passage or text.",
      type: "suggestion",
      dismissed: false,
    },
  ],
  vocabulary: [ // Placeholder
    {
      id: "v1",
      word: "雰囲気",
      reading: "ふんいき",
      romaji: "fun'iki",
      partOfSpeech: "noun",
      definition: "atmosphere, ambiance",
      example: "レストランの雰囲気も素晴らしかったです。",
      level: "intermediate",
      saved: false,
    },
    {
      id: "v2",
      word: "緊張",
      reading: "きんちょう",
      romaji: "kinchō",
      partOfSpeech: "noun, verb (する)",
      definition: "tension, nervousness, to be nervous",
      example: "私は少し緊張しました。",
      level: "intermediate",
      saved: false,
    },
    {
      id: "v3",
      word: "複雑",
      reading: "ふくざつ",
      romaji: "fukuzatsu",
      partOfSpeech: "na-adjective",
      definition: "complex, complicated",
      example: "もっと複雑な文章で注文してみたいです。",
      level: "intermediate",
      saved: false,
    },
    {
      id: "v4",
      word: "注文",
      reading: "ちゅうもん",
      romaji: "chūmon",
      partOfSpeech: "noun, verb (する)",
      definition: "order, to order",
      example: "私は日本語で注文しようとしました。",
      level: "beginner",
      saved: true,
    },
  ],
}

// Helper to get language emoji (you might want to move this to a utils file)
const getLanguageEmoji = (languageCode?: string): string => {
  if (!languageCode) return "📝";
  switch (languageCode.toLowerCase()) {
    case "ja": return "🇯🇵";
    case "en": return "🇬🇧";
    case "es": return "🇪🇸";
    case "fr": return "🇫🇷";
    case "de": return "🇩🇪";
    // Add more language codes and their emojis as needed
    default: return "📝";
  }
};


export default function EntryInsightPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [entry, setEntry] = useState<MockEntryType | null>(null) // Use MockEntryType for the state
  const [showTranslation, setShowTranslation] = useState(false)
  const [isFavorite, setIsFavorite] = useState(false) // This will use mockEntryData's isFavorite initially
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    async function fetchEntryData() {
      if (!params.id || typeof params.id !== 'string') {
        setLoading(false);
        // Optionally, redirect or show an error if ID is missing/invalid
        toast({ title: "Error", description: "Invalid entry ID.", variant: "destructive" });
        router.push("/dashboard"); // Example redirect
        return;
      }

      try {
        const fetchedEntryData = await getEntryById(params.id as string)
        if (fetchedEntryData) {
          // Combine fetched data with mock data for fields not yet in API response
          const combinedEntryData: MockEntryType = {
            ...mockEntryData, // Start with mock data as a base for placeholders
            id: fetchedEntryData.id || mockEntryData.id,
            title: fetchedEntryData.title || mockEntryData.title, // Use fetched title or fallback to mock
            language: fetchedEntryData.language || mockEntryData.language, // Use fetched language or fallback to mock
            // Assuming languageCode and languageEmoji might not be directly in fetchedEntryData.Entry
            // If they are, use them: fetchedEntryData.languageCode || mockEntryData.languageCode
            // For now, we derive emoji from language if possible, or use mock
            languageCode: fetchedEntryData.language ? mapLanguageToCode(fetchedEntryData.language) : mockEntryData.languageCode,
            languageEmoji: fetchedEntryData.language ? getLanguageEmoji(mapLanguageToCode(fetchedEntryData.language)) : mockEntryData.languageEmoji,
            content: fetchedEntryData.original_text || mockEntryData.content, // Use fetched original_text for content
            date: fetchedEntryData.created_at || mockEntryData.date, // Use created_at for date
             // Keep using mock for these until API provides them
            translation: mockEntryData.translation,
            isFavorite: mockEntryData.isFavorite, // This will be the mock's initial favorite state
            fluencyScore: mockEntryData.fluencyScore,
            grammarFeedback: mockEntryData.grammarFeedback,
            vocabulary: mockEntryData.vocabulary,
          };
          setEntry(combinedEntryData);
          setIsFavorite(combinedEntryData.isFavorite); // Set favorite state based on combined/mock data
        } else {
          toast({ title: "Entry not found", description: "Could not find the requested entry.", variant: "destructive" });
          // Optionally redirect if entry not found
           router.push("/dashboard");
        }
      } catch (error) {
        console.error("Failed to fetch entry:", error)
        toast({ title: "Error", description: "Failed to load the entry.", variant: "destructive" });
      } finally {
        setLoading(false)
      }
    }

    fetchEntryData()
  }, [params.id, router, toast])

  // Helper function to map full language names to codes if your API returns full names
  // This is just an example, adjust based on your actual API data for 'language'
  const mapLanguageToCode = (languageName: string): string => {
    const name = languageName.toLowerCase();
    if (name.includes("japanese")) return "ja";
    if (name.includes("english")) return "en";
    if (name.includes("spanish")) return "es";
    if (name.includes("french")) return "fr";
    if (name.includes("german")) return "de";
    return ""; // Fallback or default code
  };

  const handleCopyText = () => {
    if (!entry) return

    navigator.clipboard.writeText(entry.content)
    setCopied(true)

    toast({
      title: "Copied to clipboard! 📋",
      description: "Your journal entry has been copied to your clipboard",
      variant: "fun",
    })

    setTimeout(() => setCopied(false), 2000)
  }

  const handleExportPDF = () => {
    toast({
      title: "Exporting PDF... 📄",
      description: "Your journal entry is being prepared for download",
      variant: "fun",
    })
  }

  const handleToggleFavorite = () => {
    // This is a local toggle for now, actual API update would be needed here
    setIsFavorite(!isFavorite);
    if (entry) {
      setEntry({ ...entry, isFavorite: !isFavorite }); // Update local entry state if needed
    }

    toast({
      title: !isFavorite ? "Added to favorites! ⭐" : "Removed from favorites",
      description: !isFavorite
        ? "This entry has been added to your favorites"
        : "This entry has been removed from your favorites",
      variant: "fun",
    })
  }

  const handleDismissGrammarFeedback = (id: string) => {
    if (!entry) return

    setEntry({
      ...entry,
      grammarFeedback: entry.grammarFeedback.map((item) => (item.id === id ? { ...item, dismissed: true } : item)),
    })

    toast({
      title: "Feedback marked as understood ✅",
      description: "Keep up the great progress!",
      variant: "fun",
    })
  }

  const handleSaveVocabulary = (id: string) => {
    if (!entry) return

    setEntry({
      ...entry,
      vocabulary: entry.vocabulary.map((item) => (item.id === id ? { ...item, saved: !item.saved } : item)),
    })

    const word = entry.vocabulary.find((item) => item.id === id)

    toast({
      title: word && !word.saved ? "Word removed from bank" : "Word added to your bank! 📚", // Corrected logic for toast
      description: word && !word.saved
        ? `"${word.word}" has been removed from your vocabulary bank`
        : `"${word?.word || 'This word'}" has been added to your vocabulary bank`,
      variant: "fun",
    })
  }

  if (loading) {
    return (
      <div className="container max-w-5xl mx-auto py-8 px-4">
        <div className="flex items-center space-x-4 mb-8">
          <Button variant="ghost" size="icon" className="rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <Skeleton className="h-10 w-64" />
        </div>

        <div className="grid gap-8">
          <Skeleton className="h-64 w-full rounded-2xl" />
          <Skeleton className="h-48 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>

        <div className="flex justify-center py-8">
          <LoadingSpinner text="Loading your insights..." />
        </div>
      </div>
    )
  }

  if (!entry) {
    return (
      <div className="container max-w-5xl mx-auto py-8 px-4 text-center">
        <h2 className="text-2xl font-bold mb-4">Entry not found</h2>
        <p className="text-muted-foreground mb-6">The entry you're looking for doesn't exist or has been removed.</p>
        <Button variant="purple" size="lg" asChild>
          <a href="/dashboard">Back to Dashboard</a>
        </Button>
      </div>
    )
  }

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4">
      {/* Header with back button */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" asChild className="hover:bg-fun-purple/10 rounded-full">
            <a href="/dashboard">
              <ArrowLeft className="h-5 w-5" />
              <span className="sr-only">Back</span>
            </a>
          </Button>
          <h1 className="text-3xl font-bold">
            <span className="fun-heading">Entry Insights</span> ✨
          </h1>
        </div>

        <div className="flex space-x-2">
          <Button variant="ghost" size="icon" onClick={handleCopyText} className="rounded-full hover:bg-fun-blue/10">
            {copied ? <Check className="h-5 w-5 text-fun-green" /> : <Copy className="h-5 w-5 text-fun-blue" />}
            <span className="sr-only">{copied ? "Copied" : "Copy text"}</span>
          </Button>

          <Button variant="ghost" size="icon" onClick={handleExportPDF} className="rounded-full hover:bg-fun-purple/10">
            <Download className="h-5 w-5 text-fun-purple" />
            <span className="sr-only">Export to PDF</span>
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggleFavorite}
            className="rounded-full hover:bg-fun-yellow/10"
          >
            {isFavorite ? (
              <Star className="h-5 w-5 text-fun-yellow fill-fun-yellow" />
            ) : (
              <StarOff className="h-5 w-5 text-muted-foreground" />
            )}
            <span className="sr-only">{isFavorite ? "Remove from favorites" : "Add to favorites"}</span>
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="grid gap-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <EntryViewer entry={entry} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <TranslationPanel entry={entry} showTranslation={showTranslation} setShowTranslation={setShowTranslation} />
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="md:col-span-2"
          >
            <GrammarFeedback feedback={entry.grammarFeedback} onDismiss={handleDismissGrammarFeedback} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <FluencyScore score={entry.fluencyScore} />
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <VocabularyPanel vocabulary={entry.vocabulary} language={entry.language} onSaveWord={handleSaveVocabulary} />
        </motion.div>
      </div>
    </div>
  )
}
