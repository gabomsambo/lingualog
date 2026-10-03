"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Sparkles, Languages, Copy, Check, ArrowRight, AlertCircle } from "lucide-react"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/use-toast"
import { Confetti } from "@/components/confetti"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { postSupportEvent, translateEntryPart } from "@/lib/api"
import { getLanguageDisplayName } from "@/i18n/languages"

interface TranslationModalProps {
  isOpen: boolean
  onClose: () => void
  entryId: string
  entryContent: string
  entryLanguage: string
  defaultTargetLanguage?: string
}

const LANGUAGE_SELECT_CODES = ["en", "es", "fr", "de", "ja", "ko", "zh", "ar", "he", "pt", "it"]

export function TranslationModal({
  isOpen,
  onClose,
  entryId,
  entryContent,
  entryLanguage,
  defaultTargetLanguage = "en",
}: TranslationModalProps) {
  const { toast } = useToast()
  const [showTranslation, setShowTranslation] = useState(false)
  const [isTranslating, setIsTranslating] = useState(false)
  const [translation, setTranslation] = useState("")
  const [providerLabel, setProviderLabel] = useState<string | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [copied, setCopied] = useState(false)
  const [targetLanguage, setTargetLanguage] = useState(defaultTargetLanguage)
  const [showConfetti, setShowConfetti] = useState(true)

  const handleTranslate = async () => {
    if (!entryId) {
      toast({
        title: "Cannot translate yet",
        description: "Your entry was not saved. You can translate from the entry page later.",
        variant: "destructive",
      })
      return
    }

    setIsTranslating(true)
    setUnavailable(false)
    setProviderLabel(null)
    postSupportEvent({ kind: "reveal_meaning", entry_id: entryId, l2: entryLanguage }).catch(() => {})

    try {
      const result = await translateEntryPart(entryId, "original", targetLanguage)
      if (result.status === "unavailable" || !result.text) {
        setUnavailable(true)
        setTranslation("")
      } else {
        setTranslation(result.text)
        setProviderLabel(result.provider_label || null)
        setShowTranslation(true)
        toast({
          title: "Translation complete! ✨",
          description: `Your entry has been translated to ${getLanguageDisplayName(targetLanguage)}`,
          variant: "fun",
        })
      }
    } catch {
      setUnavailable(true)
      toast({
        title: "Translation unavailable",
        description: "Please try again in a moment.",
        variant: "destructive",
      })
    } finally {
      setIsTranslating(false)
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(translation)
    setCopied(true)

    toast({
      title: "Copied to clipboard! 📋",
      description: "Translation has been copied to your clipboard",
      variant: "fun",
    })

    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <>
      {showConfetti && isOpen && <Confetti count={50} />}

      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="sm:max-w-[700px] p-0 rounded-3xl border-fun-purple/30 overflow-hidden bg-gradient-to-br from-white to-fun-blue/5">
          <DialogHeader className="p-6 pb-2">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              <DialogTitle className="text-3xl font-bold text-center flex justify-center items-center gap-2">
                <Sparkles className="h-6 w-6 text-fun-yellow animate-pulse-gentle" />
                <span className="fun-heading">Entry Saved! ✨</span>
                <Sparkles className="h-6 w-6 text-fun-yellow animate-pulse-gentle" />
              </DialogTitle>
              <DialogDescription className="text-center text-lg mt-3">
                Would you like to view your writing translated into your native language?
              </DialogDescription>
            </motion.div>
          </DialogHeader>

          <AnimatePresence>
            {!showTranslation ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="p-6 flex flex-col items-center gap-6"
              >
                <div className="w-full max-w-xs">
                  <label className="text-sm font-medium mb-2 block text-center">Translate to:</label>
                  <Select value={targetLanguage} onValueChange={setTargetLanguage}>
                    <SelectTrigger className="w-full h-12 rounded-xl border-fun-purple/30 bg-white/80">
                      <SelectValue placeholder="Select language" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl border-fun-purple/30">
                      {LANGUAGE_SELECT_CODES.map((code) => (
                        <SelectItem key={code} value={code}>
                          {getLanguageDisplayName(code)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {unavailable && (
                  <div className="flex items-center gap-2 text-sm text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    Translation unavailable · Retry
                  </div>
                )}

                <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      onClick={handleTranslate}
                      disabled={isTranslating}
                      className="w-full sm:w-auto bg-gradient-to-r from-fun-green to-fun-blue text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 text-lg h-12 px-8"
                    >
                      {isTranslating ? (
                        <div className="flex items-center">
                          <div className="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                          <span className="ml-2">Translating...</span>
                        </div>
                      ) : (
                        <>
                          <Languages className="mr-2 h-5 w-5" /> Show Translation
                        </>
                      )}
                    </Button>
                  </motion.div>

                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      onClick={onClose}
                      variant="outline"
                      className="w-full sm:w-auto border-muted-foreground/30 hover:bg-muted/20 rounded-full text-lg h-12 px-8"
                    >
                      No Thanks
                    </Button>
                  </motion.div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="p-6 pt-0"
              >
                <div className="flex flex-col md:flex-row gap-4 mb-6 mt-2">
                  <div className="flex-1 p-4 bg-fun-purple/5 rounded-2xl border-2 border-fun-purple/20">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-medium text-fun-purple">
                        Original ({getLanguageDisplayName(entryLanguage)})
                      </h3>
                    </div>
                    <div className="prose max-w-none text-sm">
                      {entryContent.split("\n").map((paragraph, i) => (
                        <p key={i}>{paragraph}</p>
                      ))}
                    </div>
                  </div>

                  <div className="hidden md:flex items-center justify-center">
                    <div className="h-full flex items-center">
                      <ArrowRight className="h-5 w-5 text-fun-purple/50" />
                    </div>
                  </div>

                  <div className="flex-1 p-4 bg-fun-green/5 rounded-2xl border-2 border-fun-green/20">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-medium text-fun-green">
                        Translation ({getLanguageDisplayName(targetLanguage)})
                      </h3>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={copyToClipboard}
                        className="h-8 rounded-full hover:bg-fun-green/10 text-fun-green"
                      >
                        {copied ? <Check className="h-4 w-4 mr-1" /> : <Copy className="h-4 w-4 mr-1" />}
                        {copied ? "Copied!" : "Copy"}
                      </Button>
                    </div>
                    {providerLabel && (
                      <p className="text-xs text-muted-foreground mb-2">{providerLabel}</p>
                    )}
                    <div className="prose max-w-none text-sm">
                      {translation.split("\n").map((paragraph, i) => (
                        <p key={i}>{paragraph}</p>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex justify-center">
                  <Button
                    onClick={onClose}
                    variant="outline"
                    className="border-fun-purple/30 hover:bg-fun-purple/10 rounded-full"
                  >
                    Close
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="p-6 pt-0 text-center"
          >
            <p className="text-muted-foreground italic">Every word you practice brings you closer to fluency! 🌟</p>
          </motion.div>
        </DialogContent>
      </Dialog>
    </>
  )
}
