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
import { Feather, RefreshCw, AlertCircle, Copy, Save, Eye, EyeOff, ChevronDown, Settings, Languages, ArrowRight } from "lucide-react"
import Link from "next/link"

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
import { EntrySideBySide } from "@/components/entry-side-by-side"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Slider } from "@/components/ui/slider"

import { ApiError, getEntryById, postLogEntry, getUserSettings, type JournalEntryOverrides, type UserSettingsData } from "@/lib/api"
import { toSideBySideEntry, type SideBySideEntry } from "@/lib/side-by-side"
import type { Entry } from "@/types/entry"
import { useLocale } from "@/i18n/LocaleProvider"
import { isRTL } from "@/i18n/rtl"
import { LANGUAGES, getLanguageDisplayName } from "@/i18n/languages"

export function JournalEditor() {
  const { t } = useLocale()
  const { toast } = useToast()

  // Main content state
  const [text, setText] = useState("")
  const [title, setTitle] = useState("")
  const [targetLanguage, setTargetLanguage] = useState("es") // Language code
  const [wordCount, setWordCount] = useState(0)
  
  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Entry | null>(null)
  const [savedEntryId, setSavedEntryId] = useState<string | null>(null)
  const [resultEntry, setResultEntry] = useState<SideBySideEntry | null>(null)
  const [isTranslationModalOpen, setIsTranslationModalOpen] = useState(false)
  const [showTranslation, setShowTranslation] = useState(true)
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // User settings and overrides
  const [userSettings, setUserSettings] = useState<UserSettingsData | null>(null)
  const [overrides, setOverrides] = useState<JournalEntryOverrides>({})

  // Load user settings on mount
  useEffect(() => {
    const loadUserSettings = async () => {
      try {
        const settings = await getUserSettings()
        setUserSettings(settings)
        
        // Set default target language from user settings
        if (settings.default_target_lang) {
          setTargetLanguage(settings.default_target_lang)
        }
      } catch (error) {
        console.error('Failed to load user settings:', error)
        // Continue with defaults if settings can't be loaded
      }
    }
    
    loadUserSettings()
  }, [])

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
   * Load the saved entry so the result renders from the same data as the entry page
   */
  const loadResultEntry = async (entryId: string) => {
    try {
      const saved = await getEntryById(entryId)
      setResultEntry(saved ? toSideBySideEntry(saved) : null)
    } catch (loadError) {
      console.error("Failed to load the saved entry:", loadError)
    }
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
      
      // Build overrides with target language
      const submissionOverrides: JournalEntryOverrides = {
        target_language: targetLanguage,
        ...overrides
      }
      
      // Use the API helper function with overrides
      const data = await postLogEntry(text, title, targetLanguage, submissionOverrides);
      console.log("Entry submission successful:", data);
      
      // Show success message
      toast({
        title: t('journal.entrySubmittedSuccess'),
        description: t('journal.entrySubmittedDesc'),
      });
      
      setResult(data);
      const entryId = (data as { entry_id?: string; id?: string }).entry_id || data.id || null
      setSavedEntryId(entryId);
      // The side-by-side result replaces the pop-up; the pop-up stays one tap away.
      if (entryId) await loadResultEntry(entryId)
    } catch (error: any) {
      console.error("Error submitting entry:", error);
      const failedEntryId = error instanceof ApiError && error.status === 503 ? error.detail?.entry_id : null
      if (failedEntryId) {
        setSavedEntryId(failedEntryId)
        setError(t('journal.entryAnalysisFailed'))
        await loadResultEntry(failedEntryId)
      } else {
        setError(t('journal.failedToSubmit'));
      }
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
    setTargetLanguage(userSettings?.default_target_lang || "es")
    setWordCount(0)
    setResult(null)
    setResultEntry(null)
    setSavedEntryId(null)
    setError(null)
    setOverrides({})
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


  /**
   * Get the current target language object
   */
  const getCurrentLanguage = () => {
    return LANGUAGES.find(l => l.code === targetLanguage) || LANGUAGES[1] // Default to Spanish
  }

  const savedImmersionLevel = userSettings?.language_profiles?.find((row) => row.l2 === targetLanguage)?.immersion_level
    ?? userSettings?.immersion_level
    ?? 1
  const displayedImmersionLevel = overrides.immersion_level ?? savedImmersionLevel

  const handleCloseTranslationModal = () => {
    setIsTranslationModalOpen(false);
  };

  return (
    <div className="space-y-6">
      <Card className="border-fun-purple/20 shadow-fun rounded-3xl overflow-hidden">
        <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-pink/10 pb-4">
          <CardTitle className="text-2xl flex items-center">
            <Feather className="mr-2 h-6 w-6 text-fun-purple" />
            <span className="fun-heading">{t('journal.newEntry')}</span>
          </CardTitle>
          <p className="text-sm text-muted-foreground pt-1">{t('journal.writeEntry')}</p>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            <Input
              placeholder={t('journal.entryTitle')}
              className="text-lg"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isSubmitting}
            />

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">{t('journal.targetLanguage')}</label>
                <Select value={targetLanguage} onValueChange={(value) => {
                  setTargetLanguage(value)
                  setOverrides((prev) => {
                    const next = { ...prev }
                    delete next.immersion_level
                    return next
                  })
                }} disabled={isSubmitting}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('journal.selectTargetLanguage')} />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        <div className="flex items-center gap-2">
                          <span>{lang.flag}</span>
                          <span>{lang.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end justify-end text-sm text-muted-foreground pr-2">
                {t('journal.wordCount')}: {wordCount}
              </div>
            </div>

            <Textarea
              placeholder={t('journal.writeThoughtsIn', { language: getLanguageDisplayName(targetLanguage) })}
              className="min-h-[200px] text-base font-serif"
              value={text}
              onChange={handleTextChange}
              disabled={isSubmitting}
              lang={targetLanguage}
              dir={isRTL(targetLanguage) ? 'rtl' : 'ltr'}
            />

            {/* Advanced Options */}
            <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full h-auto p-2 justify-between">
                  <div className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    <span>{t('journal.advancedOptions')}</span>
                  </div>
                  <ChevronDown className={`h-4 w-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-4 pt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">{t('journal.explanationMode')}</label>
                    <p className="text-xs text-muted-foreground mb-2">{t('journal.explanationModeHint')}</p>
                    <Select value={overrides.explanation_mode || ''} onValueChange={(value) => setOverrides(prev => ({ ...prev, explanation_mode: value }))}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('settings.explanationMode')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="native_only">{t('settings.explanationNativeOnly')}</SelectItem>
                        <SelectItem value="target_only">{t('settings.explanationTargetOnly')}</SelectItem>
                        <SelectItem value="bilingual">{t('settings.explanationBilingual')}</SelectItem>
                        <SelectItem value="smart">{t('settings.explanationSmart')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">{t('journal.strictnessLevel')}</label>
                    <Select value={overrides.strictness || ''} onValueChange={(value) => setOverrides(prev => ({ ...prev, strictness: value }))}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('settings.strictness')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gentle">{t('settings.strictnessGentle')}</SelectItem>
                        <SelectItem value="medium">{t('settings.strictnessMedium')}</SelectItem>
                        <SelectItem value="strict">{t('settings.strictnessStrict')}</SelectItem>
                        <SelectItem value="pedantic">{t('settings.strictnessPedantic')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">
                    {t('journal.immersionLevel')}: {displayedImmersionLevel}
                  </label>
                  <p className="text-xs text-muted-foreground mb-2">{t('journal.immersionSliderHint')}</p>
                  <Slider
                    value={[displayedImmersionLevel]}
                    onValueChange={(value) => setOverrides(prev => ({ ...prev, immersion_level: value[0] }))}
                    max={3}
                    min={0}
                    step={1}
                    className="mt-2"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>0: {t('settings.immersionNativeFirst')}</span>
                    <span>1: {t('settings.immersionGuidedBilingual')}</span>
                    <span>2: {t('settings.immersionBalanced')}</span>
                    <span>3: {t('settings.immersionImmersive')}</span>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
            
            {error && (
              <Alert variant="destructive" className="bg-red-50 border-red-200 text-red-800">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="flex justify-end gap-2">
              {(result || resultEntry) && !isSubmitting && (
                <Button variant="outline" onClick={handleReset} className="rounded-full h-14 px-8 text-lg">
                  <RefreshCw className="mr-2 h-5 w-5" />
                  {t('journal.reset')}
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
                      <span className="ml-2">{t('journal.processing')}</span>
                    </div>
                  ) : (
                    <>
                      <Save className="mr-2 h-5 w-5" /> 
                      {t('journal.submitAndAnalyze')}
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
            <LoadingSpinner text={t('journal.analyzing')} />
          </motion.div>
        )}
      </AnimatePresence>

      {resultEntry && !isSubmitting && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-4"
          data-testid="post-submit-result"
        >
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsTranslationModalOpen(true)}>
              <Languages className="mr-2 h-4 w-4" />
              {t('journal.translateWholeEntry')}
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/entries/${resultEntry.id}`}>
                {t('journal.openEntryPage')}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
          <div className="lg:-mx-12 xl:-mx-32">
            <EntrySideBySide entry={resultEntry} onReanalyzed={() => loadResultEntry(resultEntry.id)} />
          </div>
        </motion.div>
      )}

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
                  <span className="fun-heading">{t('journal.feedbackResults')}</span>
                  <Badge variant={getToneBadgeVariant(result.tone)} className="ml-2">
                    {result.tone}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-6">
                  {/* Score */}
                  <div className="flex items-center gap-2">
                    <div className="font-medium text-sm text-muted-foreground">{t('journal.fluencyScore')}:</div>
                    <div className="flex items-center">
                      <span className="text-xl font-bold text-fun-green">{result.score}</span>
                      <span className="text-muted-foreground text-sm">/100</span>
                    </div>
                  </div>

                  {/* Rewrite */}
                  <div className="space-y-2">
                    <h3 className="font-medium text-fun-blue">{t('journal.nativeLikeRewrite')}:</h3>
                    <div className="p-4 bg-fun-blue/5 rounded-2xl border-2 border-fun-blue/20">
                      <p className="text-base font-serif">{(result as { rewritten?: string }).rewritten || (result as { rewrite?: string }).rewrite}</p>
                    </div>
                  </div>

                  {/* Translation with visibility toggle */}
                  {result.translation && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium text-fun-purple">{t('journal.translation')}:</h3>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowTranslation(!showTranslation)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          {showTranslation ? (
                            <>
                              <EyeOff className="h-4 w-4 mr-1" />
                              {t('journal.hideTranslation')}
                            </>
                          ) : (
                            <>
                              <Eye className="h-4 w-4 mr-1" />
                              {t('journal.showTranslation')}
                            </>
                          )}
                        </Button>
                      </div>
                      {showTranslation && (
                        <div className="p-4 bg-fun-purple/5 rounded-2xl border-2 border-fun-purple/20">
                          <p className="text-base">{result.translation}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Render the v0 TranslationModal */}
      {(result || resultEntry) && (
        <TranslationModal
          isOpen={isTranslationModalOpen}
          onClose={handleCloseTranslationModal}
          entryId={savedEntryId || ""}
          entryContent={text}
          entryLanguage={targetLanguage}
          defaultTargetLanguage={userSettings?.native_lang || userSettings?.native_language || "en"}
        />
      )}
    </div>
  )
} 