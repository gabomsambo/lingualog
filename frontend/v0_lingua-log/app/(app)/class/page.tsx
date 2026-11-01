"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowRight, Plus, Sparkles, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useLocale } from "@/i18n/LocaleProvider"
import {
  addVocabularyItem,
  confirmClassNote,
  createClassNote,
  getClassNote,
  getUserSettings,
  type ClassNoteRecord,
  type ClassNoteWord,
  type UserSettingsData,
} from "@/lib/api"
import { getLanguageDisplayName, LANGUAGES } from "@/i18n/languages"

type PagePhase = "paste" | "review"

function noteFromClass(note: ClassNoteRecord) {
  return {
    words: note.extracted.words.map(({ word_id: _wordId, encounter_id: _encounterId, ...word }) => word),
    grammar_focus: note.extracted.grammar_focus,
    phrases: note.extracted.phrases,
    tasks: note.extracted.tasks,
    level: note.extracted.level,
    length_hint: note.extracted.length_hint,
    grammar_scope: note.extracted.grammar_scope,
  }
}

export default function ClassPage() {
  const router = useRouter()
  const { t } = useLocale()
  const loadErrorText = t("journal.classNoteLoadFailed")
  const [settings, setSettings] = useState<UserSettingsData | null>(null)
  const [language, setLanguage] = useState("es")
  const [phase, setPhase] = useState<PagePhase>("paste")
  const [rawText, setRawText] = useState("")
  const [note, setNote] = useState<ClassNoteRecord | null>(null)
  const [words, setWords] = useState<ClassNoteWord[]>([])
  const [phrases, setPhrases] = useState<string[]>([])
  const [grammarFocus, setGrammarFocus] = useState("")
  const [newWord, setNewWord] = useState("")
  const [newPhrase, setNewPhrase] = useState("")
  const [selectedTask, setSelectedTask] = useState(0)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState("")

  const activeLanguages = useMemo(
    () => settings?.language_profiles?.filter((profile) => profile.active !== false).map((profile) => profile.l2) || [],
    [settings],
  )

  useEffect(() => {
    let active = true
    const noteId = new URLSearchParams(window.location.search).get("note_id")
    Promise.all([getUserSettings(), noteId ? getClassNote(noteId) : Promise.resolve(null)])
      .then(([savedSettings, savedNote]) => {
        if (!active) return
        setSettings(savedSettings)
        const selectedLanguage = savedNote?.l2 || savedSettings.default_target_lang || "es"
        setLanguage(selectedLanguage)
        if (savedNote) {
          setNote(savedNote)
          setRawText(savedNote.raw_text)
          setWords(savedNote.extracted.words)
          setGrammarFocus(savedNote.extracted.grammar_focus || "")
          setPhrases(savedNote.extracted.phrases)
          setPhase("review")
        }
        setLoading(false)
      })
      .catch((loadError) => {
        console.error("Could not load class-note details:", loadError)
        if (active) {
          setError(loadErrorText)
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [loadErrorText])

  const handleExtract = async () => {
    if (!rawText.trim() || working) return
    setWorking(true)
    setError("")
    try {
      const created = await createClassNote(rawText, language)
      setNote(created)
      setWords(created.extracted.words)
      setGrammarFocus(created.extracted.grammar_focus || "")
      setPhrases(created.extracted.phrases)
      setSelectedTask(0)
      setPhase("review")
    } catch (extractError) {
      console.error("Could not extract class material:", extractError)
      setError(t("journal.classNoteError"))
    } finally {
      setWorking(false)
    }
  }

  const updateWord = (index: number, field: "term" | "gloss", value: string) => {
    setWords((current) => current.map((word, at) => at === index
      ? { ...word, [field]: value, ...(field === "term" ? { lemma: value } : {}) }
      : word))
  }

  const addWord = () => {
    const term = newWord.trim()
    if (!term) return
    setWords((current) => [...current, {
      term,
      lemma: term,
      gloss: "",
      part_of_speech: "",
      example: "",
      reading: "",
    }])
    setNewWord("")
  }

  const addPhrase = () => {
    const phrase = newPhrase.trim()
    if (!phrase) return
    setPhrases((current) => [...current, phrase])
    setNewPhrase("")
  }

  const handlePractice = async () => {
    if (!note || working) return
    const taskIndex = Math.min(selectedTask, Math.max(note.extracted.tasks.length - 1, 0))
    setWorking(true)
    setError("")
    try {
      const confirmed = await confirmClassNote(note.id, {
        ...noteFromClass(note),
        words: words.filter((word) => word.term.trim()).map((word) => ({
          ...word,
          term: word.term.trim(),
          lemma: (word.lemma || word.term).trim(),
          gloss: word.gloss.trim(),
        })),
        grammar_focus: grammarFocus.trim() || null,
        phrases: phrases.map((phrase) => phrase.trim()).filter(Boolean),
      })

      for (const word of confirmed.extracted.words) {
        await addVocabularyItem({
          term: word.lemma || word.term,
          language: confirmed.l2,
          part_of_speech: word.part_of_speech || undefined,
          definition: word.gloss || undefined,
          reading: word.reading || undefined,
          example_sentence: word.example || word.term,
          encounter_id: word.encounter_id || undefined,
        })
      }

      router.push(`/entries/new?class_note_id=${encodeURIComponent(note.id)}&class_task=${taskIndex}`)
    } catch (saveError) {
      console.error("Could not save class-note words:", saveError)
      setError(t("journal.classNoteSaveFailed"))
    } finally {
      setWorking(false)
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-3xl py-16 text-center text-muted-foreground">{t("common.loading")}</div>
  }

  const availableLanguages = activeLanguages.length > 0 ? activeLanguages : [language]
  const tasks = note?.extracted.tasks || []

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card className="overflow-hidden rounded-3xl border-fun-purple/20 shadow-fun">
        <CardHeader className="bg-gradient-to-r from-fun-purple/10 via-fun-blue/10 to-fun-pink/10 pb-5">
          <CardTitle className="flex items-center gap-2 text-2xl text-fun-purple">
            <Sparkles className="h-6 w-6" aria-hidden />
            {t("journal.classPageTitle")}
          </CardTitle>
          <CardDescription className="max-w-2xl text-base leading-relaxed">
            {t("journal.classPageIntro")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 p-5 sm:p-7">
          {phase === "paste" ? (
            <>
              <div className="flex flex-wrap items-end justify-between gap-3">
                <label className="space-y-2 text-sm font-semibold">
                  <span>{t("journal.classLanguage")}</span>
                  <select
                    value={language}
                    onChange={(event) => setLanguage(event.target.value)}
                    className="block h-10 min-w-48 rounded-xl border border-input bg-background px-3 text-sm"
                    aria-label={t("journal.classLanguage")}
                  >
                    {LANGUAGES.filter((item) => availableLanguages.includes(item.code)).map((item) => (
                      <option key={item.code} value={item.code}>{item.flag} {item.name}</option>
                    ))}
                    {!availableLanguages.includes(language) && (
                      <option value={language}>{getLanguageDisplayName(language)}</option>
                    )}
                  </select>
                </label>
                <p className="max-w-md text-sm text-muted-foreground">{t("journal.classPrivacy")}</p>
              </div>
              <Textarea
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                placeholder={t("journal.classPastePlaceholder")}
                className="min-h-[280px] rounded-2xl bg-white/80 text-base leading-relaxed"
                maxLength={12_000}
                aria-label={t("journal.classPastePlaceholder")}
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-muted-foreground">{rawText.length.toLocaleString()} / 12,000</span>
                <Button onClick={handleExtract} disabled={working || !rawText.trim()} className="rounded-full bg-gradient-to-r from-fun-blue to-fun-purple px-6 text-white hover:opacity-90">
                  {working ? t("journal.classExtracting") : t("journal.classExtract")}
                  {!working && <ArrowRight className="ml-2 h-4 w-4" />}
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold">{t("journal.classReviewTitle")}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{t("journal.classReviewHint")}</p>
                </div>
                <span className="rounded-full bg-fun-purple/10 px-3 py-1 text-xs font-bold text-fun-purple">
                  {note?.extracted.level || "A2"} · {getLanguageDisplayName(language)}
                </span>
              </div>

              <section className="space-y-3 rounded-2xl border border-fun-yellow/40 bg-fun-yellow/10 p-4" data-testid="class-note-words">
                <div>
                  <h3 className="font-bold">{t("journal.classWordsTitle", { count: words.length })}</h3>
                  <p className="text-sm text-muted-foreground">{t("journal.classWordsHint")}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {words.map((word, index) => (
                    <div key={`${word.lemma}-${index}`} className="flex max-w-full items-center gap-1 rounded-full border border-fun-yellow/60 bg-background px-2 py-1 shadow-sm">
                      <Input
                        value={word.term}
                        onChange={(event) => updateWord(index, "term", event.target.value)}
                        className="h-8 w-32 border-0 bg-transparent px-2 font-serif text-sm font-semibold shadow-none focus-visible:ring-1"
                        aria-label={t("journal.classWordTerm")}
                      />
                      <Input
                        value={word.gloss}
                        onChange={(event) => updateWord(index, "gloss", event.target.value)}
                        placeholder={t("journal.classWordGloss")}
                        className="h-8 w-28 border-0 bg-transparent px-2 text-xs text-muted-foreground shadow-none focus-visible:ring-1"
                        aria-label={t("journal.classWordGloss")}
                      />
                      <button type="button" onClick={() => setWords((current) => current.filter((_item, at) => at !== index))} aria-label={t("journal.classRemoveWord")} className="rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
                <div className="flex max-w-sm gap-2">
                  <Input value={newWord} onChange={(event) => setNewWord(event.target.value)} placeholder={t("journal.classAddWordPlaceholder")} onKeyDown={(event) => event.key === "Enter" && (event.preventDefault(), addWord())} />
                  <Button type="button" variant="outline" onClick={addWord} aria-label={t("journal.classAddWord")}><Plus className="mr-1 h-4 w-4" />{t("journal.classAddWord")}</Button>
                </div>
              </section>

              <section className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 rounded-2xl border border-fun-blue/25 bg-fun-blue/5 p-4 text-sm font-bold">
                  <span>{t("journal.classGrammarFocus")}</span>
                  <Input value={grammarFocus} onChange={(event) => setGrammarFocus(event.target.value)} placeholder={t("journal.classGrammarPlaceholder")} className="bg-background font-normal" />
                </label>
                <div className="space-y-3 rounded-2xl border border-fun-pink/25 bg-fun-pink/5 p-4">
                  <h3 className="text-sm font-bold">{t("journal.classPhrasesTitle")}</h3>
                  <div className="flex flex-wrap gap-2">
                    {phrases.map((phrase, index) => (
                      <span key={`phrase-${index}`} className="inline-flex max-w-full items-center gap-1 rounded-full border border-fun-pink/30 bg-background px-2 py-1">
                        <Input
                          value={phrase}
                          onChange={(event) => setPhrases((current) => current.map((item, at) => at === index ? event.target.value : item))}
                          className="h-8 w-40 border-0 bg-transparent px-2 text-sm shadow-none focus-visible:ring-1"
                          aria-label={`${t("journal.classPhraseTerm")} ${index + 1}`}
                        />
                        <button type="button" onClick={() => setPhrases((current) => current.filter((_item, at) => at !== index))} aria-label={t("journal.classRemovePhrase")} className="rounded-full p-0.5 text-muted-foreground hover:text-foreground">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input value={newPhrase} onChange={(event) => setNewPhrase(event.target.value)} placeholder={t("journal.classAddPhrasePlaceholder")} onKeyDown={(event) => event.key === "Enter" && (event.preventDefault(), addPhrase())} />
                    <Button type="button" variant="outline" onClick={addPhrase} aria-label={t("journal.classAddPhrase")}><Plus className="mr-1 h-4 w-4" />{t("journal.classAddPhrase")}</Button>
                  </div>
                </div>
              </section>

              {tasks.length > 0 && (
                <section className="space-y-3" data-testid="class-practice-tasks">
                  <div>
                    <h3 className="text-lg font-bold">{t("journal.classTasksTitle")}</h3>
                    <p className="text-sm text-muted-foreground">{t("journal.classTasksHint")}</p>
                  </div>
                  <div className="grid gap-3 lg:grid-cols-3">
                    {tasks.map((task, index) => (
                      <button
                        key={`${task.title}-${index}`}
                        type="button"
                        aria-pressed={selectedTask === index}
                        onClick={() => setSelectedTask(index)}
                        className={`rounded-2xl border-2 p-4 text-left transition-colors ${selectedTask === index ? "border-fun-purple bg-fun-purple/5 shadow-sm" : "border-border bg-background hover:border-fun-purple/40"}`}
                      >
                        <span className="mb-3 inline-flex rounded-full bg-fun-blue/10 px-2.5 py-1 text-xs font-bold text-fun-blue">{task.title}</span>
                        <span className="block font-semibold leading-relaxed">{task.prompt}</span>
                        <span className="mt-3 block text-xs text-muted-foreground">{t("journal.classTaskLength", { length: task.length_hint })}</span>
                        {task.grammar_scope && <span className="mt-1 block text-xs text-muted-foreground">{t("journal.classTaskScope", { scope: task.grammar_scope })}</span>}
                      </button>
                    ))}
                  </div>
                </section>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                <Button type="button" variant="ghost" onClick={() => setPhase("paste")} disabled={working}>
                  {t("journal.classEditPaste")}
                </Button>
                <Button onClick={handlePractice} disabled={working || !note} className="rounded-full bg-gradient-to-r from-fun-green to-fun-blue px-6 text-white hover:opacity-90">
                  {working ? t("journal.classSavingWords") : t("journal.classOpenEditor")}
                  {!working && <ArrowRight className="ml-2 h-4 w-4" />}
                </Button>
              </div>
            </>
          )}

          {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
