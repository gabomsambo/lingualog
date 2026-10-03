"use client"

import { useCallback, useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Languages, ThumbsUp, ThumbsDown, ArrowRight, AlertCircle, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { postSupportEvent, translateEntryPart } from "@/lib/api"
import { getLanguageDisplayName } from "@/i18n/languages"

interface TranslationPanelProps {
  entryId: string
  entry: {
    language: string
    languageCode?: string
    content: string
  }
  nativeLanguage: string
  immersionLevel?: number
  showTranslation: boolean
  setShowTranslation: (show: boolean) => void
}

export function TranslationPanel({
  entryId,
  entry,
  nativeLanguage,
  immersionLevel,
  showTranslation,
  setShowTranslation,
}: TranslationPanelProps) {
  const { toast } = useToast()
  const [translationRated, setTranslationRated] = useState(false)
  const [translation, setTranslation] = useState("")
  const [providerLabel, setProviderLabel] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [unavailable, setUnavailable] = useState(false)
  const [attempted, setAttempted] = useState(false)

  const loadTranslation = useCallback(async () => {
    if (!entryId) return
    setLoading(true)
    setUnavailable(false)
    try {
      const result = await translateEntryPart(entryId, "original", nativeLanguage)
      if (result.status === "unavailable" || !result.text) {
        setUnavailable(true)
        setTranslation("")
      } else {
        setTranslation(result.text)
        setProviderLabel(result.provider_label || null)
      }
    } catch {
      setUnavailable(true)
      setTranslation("")
    } finally {
      setLoading(false)
    }
  }, [entryId, nativeLanguage])

  const handleToggle = () => {
    const reveal = !showTranslation
    setShowTranslation(reveal)
    if (reveal && entryId) {
      postSupportEvent({
        kind: "reveal_meaning",
        entry_id: entryId,
        immersion_level: immersionLevel,
        l2: entry.languageCode || entry.language,
      }).catch(() => {})
    }
  }

  useEffect(() => {
    setAttempted(false)
    setTranslation("")
    setProviderLabel(null)
    setUnavailable(false)
  }, [entryId, nativeLanguage])

  useEffect(() => {
    if (showTranslation && !attempted) {
      setAttempted(true)
      void loadTranslation()
    }
  }, [showTranslation, attempted, loadTranslation])

  const handleRateTranslation = (isGood: boolean) => {
    setTranslationRated(true)

    toast({
      title: isGood ? "Thanks for your feedback! 🙌" : "Thanks for your feedback! 🙏",
      description: isGood ? "We're glad the translation was helpful!" : "We'll work on improving our translations.",
      variant: "fun",
    })
  }

  const l2Label = getLanguageDisplayName(entry.languageCode || entry.language)
  const l1Label = getLanguageDisplayName(nativeLanguage)

  return (
    <Card className="border-fun-blue/20 shadow-fun rounded-3xl overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-fun-blue/10 to-fun-teal/10 pb-4">
        <div className="flex justify-between items-center">
          <CardTitle className="text-2xl">
            <span className="fun-heading">Translation</span>
          </CardTitle>
          <Button
            onClick={handleToggle}
            variant={showTranslation ? "outline" : "blue"}
            className={`rounded-full ${showTranslation ? "border-fun-blue/30 hover:bg-fun-blue/10" : ""}`}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <Languages className="mr-2 h-5 w-5" />
            )}
            {showTranslation ? "Hide Translation" : "Show Translation"}
          </Button>
        </div>
      </CardHeader>

      <AnimatePresence>
        {showTranslation && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <CardContent className="p-6">
              {unavailable && (
                <div className="flex items-center justify-center gap-2 text-destructive mb-4">
                  <AlertCircle className="h-5 w-5" />
                  <span>Translation unavailable</span>
                  <Button variant="link" onClick={() => void loadTranslation()}>Retry</Button>
                </div>
              )}
              <div className="flex flex-col md:flex-row gap-6">
                <div className="flex-1 p-4 bg-fun-purple/5 rounded-2xl border-2 border-fun-purple/20">
                  <h3 className="font-medium text-fun-purple mb-3">Original ({l2Label})</h3>
                  <div className="prose max-w-none text-base font-serif">
                    {entry.content.split("\n\n").map((paragraph, index) => (
                      <p key={index} className="mb-4 leading-relaxed">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>

                <div className="hidden md:flex items-center justify-center">
                  <div className="h-full flex items-center">
                    <ArrowRight className="h-5 w-5 text-fun-blue/50" />
                  </div>
                </div>

                <div className="flex-1 p-4 bg-fun-blue/5 rounded-2xl border-2 border-fun-blue/20">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-medium text-fun-blue">What it means ({l1Label})</h3>

                    {!translationRated && translation && (
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">Helpful?</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRateTranslation(true)}
                          className="h-8 w-8 p-0 rounded-full hover:bg-fun-green/10"
                        >
                          <ThumbsUp className="h-4 w-4 text-fun-green" />
                          <span className="sr-only">Good translation</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRateTranslation(false)}
                          className="h-8 w-8 p-0 rounded-full hover:bg-fun-pink/10"
                        >
                          <ThumbsDown className="h-4 w-4 text-fun-pink" />
                          <span className="sr-only">Bad translation</span>
                        </Button>
                      </div>
                    )}
                  </div>

                  {providerLabel && (
                    <p className="text-xs text-muted-foreground mb-2">{providerLabel}</p>
                  )}

                  <div className="prose max-w-none text-base">
                    {loading && !translation ? (
                      <p className="text-muted-foreground">Loading translation…</p>
                    ) : (
                      translation.split("\n\n").map((paragraph, index) => (
                        <p key={index} className="mb-4 leading-relaxed">
                          {paragraph}
                        </p>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}
