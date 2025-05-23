"use client"

/**
 * JournalEditor Component
 * 
 * Provides a text input area for users to write journal entries in their target
 * language and submit them for AI feedback. Displays the feedback results including
 * rewrite suggestions, fluency score, and tone analysis.
 * 
 * @component
 */

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Feather, RefreshCw, AlertCircle, Copy, Save } from "lucide-react"
import { useRouter } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { LoadingSpinner } from "@/components/loading-spinner"
import { LoadingDots } from "@/components/loading-dots"
import { useToast } from "@/components/ui/use-toast"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TranslationModal } from "@/components/translation-modal"

import { postLogEntry } from "@/lib/api"
import type { Entry } from "@/types/entry"

export function JournalEditor() {
  const [text, setText] = useState("")
  const [title, setTitle] = useState("")
  const [language, setLanguage] = useState("English") // Default language
  const [wordCount, setWordCount] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Entry | null>(null)
  const [isTranslationModalOpen, setIsTranslationModalOpen] = useState(false)
  const router = useRouter()
  const { toast } = useToast()

  /**
   * Handle text input changes
   */
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value
    setText(newText)
    // Calculate word count
    setWordCount(newText.trim().split(/\s+/).filter(Boolean).length)
    // Clear any previous errors when user starts typing again
    if (error) setError(null)
  }

  /**
   * Handle the journal entry submission
   */
  const handleSubmit = async () => {
    if (text.length < 5) return
    
    setIsSubmitting(true)
    setError(null)
    
    try {
      console.log("Submitting entry to API...")
      
      // Use the API helper function instead of direct fetch
      // TODO: Include title and language in the submission
      const data = await postLogEntry(text, title, language);
      console.log("Entry submission successful:", data);
      
      // Show success message
      toast({
        title: "Entry submitted successfully!",
        description: "Your journal entry has been saved and analyzed.",
      });
      
      setResult(data);
      setIsTranslationModalOpen(true) // Show the new v0 TranslationModal
      
      // router.push(`/entries`); // Navigation will be handled by the modal's onClose
    } catch (error: any) {
      console.error("Error submitting entry:", error);
      setError(`Failed to submit entry. Is the backend running?`);
    } finally {
      setIsSubmitting(false)
    }
  }

  /**
   * Reset the form and results
   */
  const handleReset = () => {
    setText("")
    setTitle("")
    setLanguage("English")
    setWordCount(0)
    setResult(null)
    setError(null)
  }

  /**
   * Get the appropriate badge variant based on tone
   */
  const getToneBadgeVariant = (tone: string) => {
    switch (tone) {
      case "Reflective":
        return "blue"
      case "Confident":
        return "green"
      case "Neutral":
      default:
        return "default" // gray
    }
  }

  const handleCloseTranslationModal = () => {
    setIsTranslationModalOpen(false);
    router.push(`/entries`);
  };

  return (
    <div className="space-y-6">
      <Card className="border-fun-purple/20 shadow-fun rounded-3xl overflow-hidden">
        <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-pink/10 pb-4">
          <CardTitle className="text-2xl flex items-center">
            <Feather className="mr-2 h-6 w-6 text-fun-purple" />
            <span className="fun-heading">Journal Entry</span>
          </CardTitle>
          <p className="text-sm text-muted-foreground pt-1">Craft your entry, select the language, and get instant feedback.</p>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            <Input
              placeholder="Entry Title"
              className="text-lg"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isSubmitting}
            />

            <div className="grid grid-cols-2 gap-4">
              <Select value={language} onValueChange={setLanguage} disabled={isSubmitting}>
                <SelectTrigger>
                  <SelectValue placeholder="Select language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="English">English</SelectItem>
                  <SelectItem value="Spanish">Spanish</SelectItem>
                  <SelectItem value="French">French</SelectItem>
                  <SelectItem value="German">German</SelectItem>
                  <SelectItem value="Japanese">Japanese</SelectItem>
                  {/* Add more languages as needed */}
                </SelectContent>
              </Select>
              <div className="flex items-center justify-end text-sm text-muted-foreground pr-2">
                Word Count: {wordCount}
              </div>
            </div>

            <Textarea
              placeholder={`Write your thoughts in ${language}...`}
              className="min-h-[200px] text-base font-serif"
              value={text}
              onChange={handleTextChange}
              disabled={isSubmitting}
            />
            
            {error && (
              <Alert variant="destructive" className="bg-red-50 border-red-200 text-red-800">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="flex justify-end gap-2">
              {result && !isSubmitting && (
                <Button variant="outline" onClick={handleReset} className="rounded-full h-14 px-8 text-lg">
                  <RefreshCw className="mr-2 h-5 w-5" />
                  Reset
                </Button>
              )}
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }} className="w-full sm:w-auto">
                <Button 
                  onClick={handleSubmit} 
                  disabled={text.length < 5 || title.length === 0 || isSubmitting}
                  className="w-full sm:w-auto bg-gradient-to-r from-fun-green to-fun-blue text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 text-lg h-14 px-8"
                >
                  {isSubmitting ? (
                    <div className="flex items-center justify-center">
                      <LoadingDots />
                      <span className="ml-2">Processing...</span>
                    </div>
                  ) : (
                    <>
                      <Save className="mr-2 h-5 w-5" /> 
                      Submit & Analyze
                    </>
                  )}
                </Button>
              </motion.div>
            </div>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {isSubmitting && !result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="flex justify-center py-8"
          >
            <LoadingSpinner text="Analyzing your writing..." />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {result && !isSubmitting && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-fun-green/20 shadow-fun rounded-3xl overflow-hidden">
              <CardHeader className="bg-gradient-to-r from-fun-green/10 to-fun-blue/10 pb-4">
                <CardTitle className="text-2xl flex items-center justify-between">
                  <span className="fun-heading">Feedback Results</span>
                  <Badge variant={getToneBadgeVariant(result.tone)} className="ml-2">
                    {result.tone}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-6">
                  {/* Score */}
                  <div className="flex items-center gap-2">
                    <div className="font-medium text-sm text-muted-foreground">Fluency Score:</div>
                    <div className="flex items-center">
                      <span className="text-xl font-bold text-fun-green">{result.score}</span>
                      <span className="text-muted-foreground text-sm">/100</span>
                    </div>
                  </div>

                  {/* Rewrite */}
                  <div className="space-y-2">
                    <h3 className="font-medium text-fun-blue">Native-like Rewrite:</h3>
                    <div className="p-4 bg-fun-blue/5 rounded-2xl border-2 border-fun-blue/20">
                      <p className="text-base font-serif">{result.rewrite}</p>
                    </div>
                  </div>

                  {/* TODO: Add corrected text display in future iteration */}
                  {/* <div className="space-y-2">
                    <h3 className="font-medium text-fun-purple">Grammar Corrections:</h3>
                    <div className="p-4 bg-fun-purple/5 rounded-2xl border-2 border-fun-purple/20">
                      <p className="text-base font-serif">{result.corrected}</p>
                    </div>
                  </div> */}

                  {/* Translation */}
                  <div className="space-y-2">
                    <h3 className="font-medium text-fun-purple">Translation:</h3>
                    <div className="p-4 bg-fun-purple/5 rounded-2xl border-2 border-fun-purple/20">
                      <p className="text-base">{result.translation}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Render the v0 TranslationModal */}
      {result && (
        <TranslationModal 
          isOpen={isTranslationModalOpen}
          onClose={handleCloseTranslationModal}
          entryContent={text} // Pass the original text content
          entryLanguage={language} // Pass the language the entry was written in
        />
      )}
    </div>
  )
} 