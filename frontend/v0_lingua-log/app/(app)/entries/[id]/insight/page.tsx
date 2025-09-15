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

// Mock entry data
const mockEntry = {
  id: "1",
  title: "Mi día en el restaurante español",
  language: "Spanish", 
  languageCode: "es",
  languageEmoji: "🇪🇸",
  date: "2025-04-21T14:30:00Z",
  content: `Hoy fui a un restaurante español con mis amigos. Comimos paella y tapas. ¡Estaba muy delicioso!

El ambiente del restaurante también era maravilloso. Sonaba música tradicional española y había cuadros hermosos en las paredes.

Intenté ordenar en español, pero estaba un poco nervioso. Sin embargo, el camarero era muy amable y entendió mi español. Me dijo "¡Su español es muy bueno!" ¡Estaba muy feliz!

La próxima vez, quiero intentar ordenar con frases más complejas. ¡Continuaré estudiando español!`,
  translation: `Today I went to a Spanish restaurant with my friends. We ate paella and tapas. It was very delicious!

The atmosphere of the restaurant was also wonderful. Traditional Spanish music was playing and there were beautiful paintings on the walls.

I tried to order in Spanish, but I was a little nervous. However, the waiter was very kind and understood my Spanish. He told me "Your Spanish is very good!" I was very happy!

Next time, I want to try ordering with more complex phrases. I will continue studying Spanish!`,
  isFavorite: false,
  fluencyScore: {
    overall: 72,
    level: "Intermediate",
    grammar: 80,
    vocabulary: 65,
    complexity: 70,
    improvement: "You're using more varied vocabulary and longer sentences!",
  },
  grammarFeedback: [
    {
      id: "g1",
      original: "Comimos paella y tapas.",
      suggested: "Comimos paella y tapas.",
      explanation: "This sentence is grammatically correct! Great job using the past tense correctly.",
      type: "positive",
      dismissed: false,
    },
    {
      id: "g2",
      original: "El ambiente del restaurante también era maravilloso.",
      suggested: "El ambiente del restaurante también era maravilloso.",
      explanation: "Perfect use of the imperfect tense to describe past conditions. Well done!",
      type: "positive",
      dismissed: false,
    },
    {
      id: "g3",
      original: "Intenté ordenar en español, pero estaba un poco nervioso.",
      suggested: "Intenté ordenar en español, pero estaba un poco nervioso.",
      explanation: "Excellent use of contrasting ideas with 'pero' and correct verb tenses.",
      type: "positive",
      dismissed: false,
    },
    {
      id: "g4",
      original: "La próxima vez, quiero intentar ordenar con frases más complejas.",
      suggested: "La próxima vez, quiero intentar pedir con frases más complejas.",
      explanation:
        "Consider using 'pedir' instead of 'ordenar' in restaurant contexts. 'Pedir' is more commonly used for ordering food.",
      type: "suggestion",
      dismissed: false,
    },
  ],
  vocabulary: [
    {
      id: "v1",
      word: "ambiente",
      reading: "",
      romaji: "",
      partOfSpeech: "noun",
      definition: "atmosphere, environment",
      example: "El ambiente del restaurante era maravilloso.",
      level: "intermediate",
      saved: false,
    },
    {
      id: "v2",
      word: "correcto",
      reading: "",
      romaji: "",
      partOfSpeech: "adjective",
      definition: "correct, right, proper",
      example: "Tu pronunciación es muy correcta.",
      level: "beginner",
      saved: false,
    },
    {
      id: "v3",
      word: "complejo",
      reading: "",
      romaji: "",
      partOfSpeech: "adjective",
      definition: "complex, complicated",
      example: "Quiero intentar frases más complejas.",
      level: "intermediate",
      saved: false,
    },
    {
      id: "v4",
      word: "ordenar",
      reading: "",
      romaji: "",
      partOfSpeech: "verb",
      definition: "to order, to arrange",
      example: "Intenté ordenar en español.",
      level: "beginner",
      saved: true,
    },
  ],
}

export default function EntryInsightPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [entry, setEntry] = useState<typeof mockEntry | null>(null)
  const [showTranslation, setShowTranslation] = useState(false)
  const [isFavorite, setIsFavorite] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    // Simulate API call to fetch entry data
    const timer = setTimeout(() => {
      setEntry(mockEntry)
      setIsFavorite(mockEntry.isFavorite)
      setLoading(false)
    }, 1500)

    return () => clearTimeout(timer)
  }, [])

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
    setIsFavorite(!isFavorite)

    toast({
      title: isFavorite ? "Removed from favorites" : "Added to favorites! ⭐",
      description: isFavorite
        ? "This entry has been removed from your favorites"
        : "This entry has been added to your favorites",
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
      title: word?.saved ? "Word removed from bank" : "Word added to your bank! 📚",
      description: word?.saved
        ? `"${word.word}" has been removed from your vocabulary bank`
        : `"${word.word}" has been added to your vocabulary bank`,
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
