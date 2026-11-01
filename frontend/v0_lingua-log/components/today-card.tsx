"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { CalendarDays, Lightbulb } from "lucide-react"

import { ReviewDueCard } from "@/components/review-due-card"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useLocale } from "@/i18n/LocaleProvider"
import { getCurrentPolicy, getPrompts, postSupportEvent, type WritingPrompt } from "@/lib/api"

export function TodayCard({ language }: { language: string }) {
  const { t } = useLocale()
  const [prompt, setPrompt] = useState<WritingPrompt | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getCurrentPolicy(language)
      .then((policy) => getPrompts({ l2: policy.l2, level: policy.proficiency || "A2" }))
      .then((response) => {
        if (!cancelled) setPrompt(response.prompts[0] || null)
      })
      .catch(() => {
        if (!cancelled) setPrompt(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [language])

  const promptFrame = prompt?.one_sentence_frame || prompt?.prompt || ""
  const startWritingHref = () => {
    if (!prompt) return "/entries/new"
    const params = new URLSearchParams({
      today_prompt_id: prompt.id,
      today_entry_mode: "one_sentence",
      today_prompt_text: prompt.prompt,
      today_prompt_frame: promptFrame,
      today_l2: language,
    })
    return `/entries/new?${params.toString()}`
  }

  return (
    <Card className="mb-8 overflow-hidden border-fun-purple/25" data-testid="today-card">
      <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-blue/10 pb-4">
        <CardTitle className="flex items-center gap-2 text-xl">
          <CalendarDays className="h-5 w-5 text-fun-purple" />
          {t("journal.todayTitle")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-4 sm:p-5">
        <ReviewDueCard embedded />
        <section className="rounded-2xl border border-fun-blue/20 bg-fun-blue/5 p-4" data-testid="today-prompt">
          <h3 className="flex items-center gap-2 text-base font-bold">
            <Lightbulb className="h-4 w-4 text-fun-blue" />
            {t("journal.todayPromptTitle")}
          </h3>
          {loading ? (
            <p className="mt-2 text-sm text-muted-foreground">{t("journal.todayPromptLoading")}</p>
          ) : prompt ? (
            <>
              <p className="mt-2 font-semibold">{prompt.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{prompt.prompt}</p>
              <Button asChild className="mt-3" size="sm">
                <Link
                  href={startWritingHref()}
                  onClick={() => {
                    postSupportEvent({ kind: "prompt_selected", l2: language, prompt_id: prompt.id }).catch(() => {})
                  }}
                  data-testid="today-write-one-sentence"
                >
                  {t("journal.todayWriteOneSentence")}
                </Link>
              </Button>
            </>
          ) : (
            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">{t("journal.todayPromptUnavailable")}</p>
              <Button asChild variant="outline" size="sm">
                <Link href="/entries/new">{t("journal.startNewEntry")}</Link>
              </Button>
            </div>
          )}
        </section>
      </CardContent>
    </Card>
  )
}
