"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Languages, ThumbsUp, ThumbsDown, ArrowRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"

interface TranslationPanelProps {
  entry: {
    language: string
    content: string
    translation: string
  }
  showTranslation: boolean
  setShowTranslation: (show: boolean) => void
}

export function TranslationPanel({ entry, showTranslation, setShowTranslation }: TranslationPanelProps) {
  const { toast } = useToast()
  const [translationRated, setTranslationRated] = useState(false)

  const handleRateTranslation = (isGood: boolean) => {
    setTranslationRated(true)

    toast({
      title: isGood ? "Thanks for your feedback! 🙌" : "Thanks for your feedback! 🙏",
      description: isGood ? "We're glad the translation was helpful!" : "We'll work on improving our translations.",
      variant: "fun",
    })
  }

  return (
    <Card className="border-fun-blue/20 shadow-fun rounded-3xl overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-fun-blue/10 to-fun-teal/10 pb-4">
        <div className="flex justify-between items-center">
          <CardTitle className="text-2xl">
            <span className="fun-heading">Translation</span>
          </CardTitle>
          <Button
            onClick={() => setShowTranslation(!showTranslation)}
            variant={showTranslation ? "outline" : "blue"}
            className={`rounded-full ${showTranslation ? "border-fun-blue/30 hover:bg-fun-blue/10" : ""}`}
          >
            <Languages className="mr-2 h-5 w-5" />
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
              <div className="flex flex-col md:flex-row gap-6">
                <div className="flex-1 p-4 bg-fun-purple/5 rounded-2xl border-2 border-fun-purple/20">
                  <h3 className="font-medium text-fun-purple mb-3">Original</h3>
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
                    <h3 className="font-medium text-fun-blue">Translation</h3>

                    {!translationRated && (
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

                  <div className="prose max-w-none text-base">
                    {entry.translation.split("\n\n").map((paragraph, index) => (
                      <p key={index} className="mb-4 leading-relaxed">
                        {paragraph}
                      </p>
                    ))}
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
