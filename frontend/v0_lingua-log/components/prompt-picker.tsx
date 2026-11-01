"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Lightbulb, RefreshCw, Sparkles } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getPrompts, type PromptEntryMode, type WritingPrompt, type WritingPromptResponse } from "@/lib/api"
import { useLocale } from "@/i18n/LocaleProvider"

interface PromptPickerProps {
  language: string
  level: string
  disabled?: boolean
  excludeIds: string[]
  resetKey: number
  onUsePrompt: (prompt: WritingPrompt, mode: PromptEntryMode) => void
  onPromptUsed: (promptId: string) => void
}

const MODES: { id: PromptEntryMode; labelKey: string; icon: typeof Lightbulb }[] = [
  { id: "idea", labelKey: "promptGiveIdea", icon: Lightbulb },
  { id: "frame", labelKey: "promptFillBlanks", icon: Sparkles },
  { id: "one_sentence", labelKey: "promptOneSentence", icon: RefreshCw },
]

const VISIBLE_PROMPTS = 3

export function PromptPicker({
  language,
  level,
  disabled = false,
  excludeIds,
  resetKey,
  onUsePrompt,
  onPromptUsed,
}: PromptPickerProps) {
  const { t } = useLocale()
  const [mode, setMode] = useState<PromptEntryMode | null>(null)
  const [topic, setTopic] = useState("all")
  const [response, setResponse] = useState<WritingPromptResponse | null>(null)
  const [shown, setShown] = useState<WritingPrompt[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [glossOpen, setGlossOpen] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const excludeRef = useRef(excludeIds)
  const requestRef = useRef(0)

  useEffect(() => {
    excludeRef.current = excludeIds
  }, [excludeIds])

  const fetchPrompts = useCallback(async (additionalExclude: string[] = [], append = false) => {
    const requestId = ++requestRef.current
    setLoading(true)
    setFailed(false)
    try {
      const excluded = [...new Set([...excludeRef.current, ...additionalExclude])]
      const data = await getPrompts({
        l2: language,
        level,
        ...(topic !== "all" ? { topic } : {}),
        exclude: excluded,
      })
      if (requestId !== requestRef.current) return
      setResponse(data)
      const remaining = data.prompts.filter((prompt) => !additionalExclude.includes(prompt.id))
      setHasMore(remaining.length > VISIBLE_PROMPTS)
      setShown((current) => {
        const next = data.prompts.filter((prompt) => !current.some((item) => item.id === prompt.id))
        return append ? [...current, ...next.slice(0, VISIBLE_PROMPTS)] : data.prompts.slice(0, VISIBLE_PROMPTS)
      })
    } catch {
      if (requestId === requestRef.current) setFailed(true)
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }, [language, level, topic])

  useEffect(() => {
    setSelectedId(null)
    setGlossOpen(new Set())
    if (mode) void fetchPrompts()
  }, [mode, language, level, topic, resetKey, fetchPrompts])

  const chooseMode = (next: PromptEntryMode) => {
    setMode(next)
    setTopic("all")
    setSelectedId(null)
  }

  const usePrompt = (prompt: WritingPrompt) => {
    if (!mode) return
    setSelectedId(prompt.id)
    onUsePrompt(prompt, mode)
    onPromptUsed(prompt.id)
  }

  const loadMore = () => {
    void fetchPrompts(shown.map((prompt) => prompt.id), true)
  }

  const glossField = mode === "idea"
    ? "prompt"
    : mode === "frame"
      ? "sentence_frame"
      : "one_sentence_frame"
  const useLabel = mode === "idea"
    ? "promptUseIdea"
    : mode === "frame"
      ? "promptUseFrame"
      : "promptUseOneSentence"

  return (
    <section className="rounded-2xl border border-fun-purple/20 bg-fun-purple/5 p-4" aria-label={t("journal.promptWaysIn")}>
      <div className="flex flex-wrap gap-2">
        {MODES.map(({ id, labelKey, icon: Icon }) => (
          <Button
            key={id}
            type="button"
            variant={mode === id ? "default" : "outline"}
            aria-pressed={mode === id}
            disabled={disabled}
            onClick={() => chooseMode(id)}
            className={`rounded-full ${mode === id ? "bg-fun-purple text-white hover:bg-fun-purple/90" : "border-fun-purple/30"}`}
          >
            <Icon className="mr-2 h-4 w-4" />
            {t(`journal.${labelKey}`)}
          </Button>
        ))}
      </div>

      {mode && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">{t("journal.promptPickerHint")}</p>
            <Select value={topic} onValueChange={(value) => setTopic(value)} disabled={disabled || loading}>
              <SelectTrigger className="h-9 w-full sm:w-52" aria-label={t("journal.promptTopicLabel")}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("journal.promptAllTopics")}</SelectItem>
                {response?.topics.map((tag) => (
                  <SelectItem key={tag} value={tag}>{t(`journal.promptTopic_${tag}`)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading && <p className="text-sm text-muted-foreground" role="status">{t("journal.promptLoading")}</p>}
          {failed && <p className="text-sm text-destructive" role="status">{t("journal.promptFailed")}</p>}
          {!loading && !failed && shown.length === 0 && (
            <p className="text-sm text-muted-foreground" data-testid="prompt-empty">{t("journal.promptsUnavailable")}</p>
          )}

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {shown.map((prompt) => {
              const gloss = prompt.gloss?.[glossField]
              const glossIsOpen = response?.meaning === "open" || glossOpen.has(prompt.id)
              const frame = mode === "idea"
                ? prompt.prompt
                : mode === "frame"
                  ? prompt.sentence_frame
                  : prompt.one_sentence_frame
              return (
                <article key={prompt.id} className="rounded-xl border border-fun-purple/15 bg-background p-4">
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <h3 className="font-medium">{prompt.title}</h3>
                    <Badge variant="purple" className="shrink-0">{prompt.level}</Badge>
                  </div>
                  <p className="font-serif text-sm leading-relaxed" lang={language}>{frame}</p>
                  <p className="mt-2 text-xs text-muted-foreground" lang={language}>{prompt.structure_hint}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t("journal.promptSuggestedWords")}: {prompt.suggested_words.join(" · ")}
                  </p>
                  {response?.gloss_available && gloss && (
                    response.meaning === "open" ? (
                      <p className="mt-2 text-sm text-muted-foreground" lang="en">{gloss}</p>
                    ) : (
                      <div className="mt-2">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-auto px-0 text-xs"
                          aria-expanded={glossIsOpen}
                          onClick={() => setGlossOpen((current) => {
                            const next = new Set(current)
                            if (next.has(prompt.id)) next.delete(prompt.id)
                            else next.add(prompt.id)
                            return next
                          })}
                        >
                          {glossIsOpen ? t("journal.promptHideGloss") : t("journal.promptShowGloss")}
                        </Button>
                        {glossIsOpen && <p className="text-sm text-muted-foreground" lang="en">{gloss}</p>}
                      </div>
                    )
                  )}
                  <Button
                    type="button"
                    variant={selectedId === prompt.id ? "default" : "outline"}
                    className="mt-3 w-full rounded-full border-fun-purple/30"
                    disabled={disabled}
                    aria-pressed={selectedId === prompt.id}
                    onClick={() => usePrompt(prompt)}
                  >
                    {t(`journal.${useLabel}`)}
                  </Button>
                </article>
              )
            })}
          </div>

          {!loading && !failed && shown.length > 0 && hasMore && (
            <Button type="button" variant="ghost" size="sm" disabled={disabled} onClick={loadMore}>
              <RefreshCw className="mr-2 h-4 w-4" />{t("journal.promptMore")}
            </Button>
          )}
        </div>
      )}
    </section>
  )
}
